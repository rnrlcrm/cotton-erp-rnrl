from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.modules.settings.router import router as settings_router
from backend.modules.partners.router import router as partners_router
from backend.api.v1.routers.user_onboarding import router as user_onboarding_router
from backend.app.middleware.security import RequestIDMiddleware, SecureHeadersMiddleware
from backend.app.middleware import AuthMiddleware, DataIsolationMiddleware
import logging, json
from logging.config import dictConfig
from pathlib import Path
import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from backend.core.settings.config import settings
from sqlalchemy import text
from backend.db.session import SessionLocal
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.core.errors.exceptions import DomainError


def create_app() -> FastAPI:
	app = FastAPI(title="Cotton ERP Backend", version="0.1.0")
	# Logging config load
	log_cfg_path = Path(__file__).resolve().parents[2] / "configs" / "logging" / "backend.json"
	if log_cfg_path.exists():
		with log_cfg_path.open() as f:
			cfg = json.load(f)
		dictConfig(cfg)
	# OpenTelemetry instrumentation (only if endpoint configured)
	otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if otlp_endpoint:
		resource = Resource(attributes={"service.name": "cotton-erp-backend"})
		provider = TracerProvider(resource=resource)
		span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
		provider.add_span_processor(BatchSpanProcessor(span_exporter))
		trace.set_tracer_provider(provider)
		FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
	# Middlewares (order matters: RequestID → Auth → Isolation → Security → CORS)
	app.add_middleware(RequestIDMiddleware)
	app.add_middleware(AuthMiddleware)
	app.add_middleware(DataIsolationMiddleware)
	app.add_middleware(SecureHeadersMiddleware)
	# CORS
	origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"] if origins == ["*"] else origins,
		allow_credentials=False,
		allow_methods=["*"],
		allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
		expose_headers=["X-Request-ID"],
	)

	# Global error handler for uniform error payloads (keep concise; add specific handlers later)
	@app.exception_handler(DomainError)
	async def _domain_err(request: Request, exc: DomainError):  # noqa: ANN001
		return JSONResponse(status_code=400, content={"error": exc.code, "detail": str(exc)})

	@app.exception_handler(RateLimitExceeded)
	async def _rate_limited(request: Request, exc: RateLimitExceeded):  # noqa: ANN001
		return JSONResponse(status_code=429, content={"error": "rate_limited", "detail": str(exc)})

	@app.exception_handler(Exception)
	async def _unhandled(request: Request, exc: Exception):  # noqa: ANN001
		return JSONResponse(status_code=500, content={"error": "internal_error"})

	# Health/readiness
	@app.get("/healthz")
	def healthz() -> dict:
		return {"status": "ok"}

	@app.get("/ready")
	def readiness() -> dict:
		try:
			with SessionLocal() as s:
				s.execute(text("SELECT 1"))
			return {"ready": True}
		except Exception:
			return {"ready": False}

	# Rate limiter: global default (e.g. 200/min per IP)
	limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
	app.state.limiter = limiter
	app.add_exception_handler(RateLimitExceeded, _rate_limited)

	# API Routers
	app.include_router(user_onboarding_router, prefix="/api/v1", tags=["auth"])
	app.include_router(partners_router, prefix="/api/v1", tags=["partners"])
	app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])
	
	# Session Management (NEW)
	from backend.modules.auth.router import router as session_router
	app.include_router(session_router, prefix="/api/v1", tags=["sessions"])
	
	# Privacy & GDPR (NEW)
	from backend.api.v1.privacy import router as privacy_router
	app.include_router(privacy_router, prefix="/api/v1", tags=["privacy"])
	
	return app


app = create_app()
