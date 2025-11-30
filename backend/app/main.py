from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.modules.settings.router import router as settings_router
from backend.modules.partners.router import router as partners_router
from backend.api.v1.routers.user_onboarding import router as user_onboarding_router
from backend.app.middleware.security import RequestIDMiddleware, SecureHeadersMiddleware
from backend.app.middleware import AuthMiddleware, DataIsolationMiddleware
from backend.app.middleware.idempotency import IdempotencyMiddleware
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
from backend.app.middleware.rate_limit import setup_rate_limiting


def create_app() -> FastAPI:
	app = FastAPI(
		title="Cotton ERP API",
		version="1.0.0",
		description="""
		## 2035-Ready Cotton Trading ERP System
		
		Complete ERP system for cotton trading with:
		- 🔐 Zero-trust security (JWT rotation, RBAC)
		- 📱 Mobile-first offline sync (WatermelonDB)
		- ⚡ Real-time updates (WebSocket sharding)
		- 📊 Event sourcing & audit trail
		- 🌐 Multi-organization support
		- 🔄 Async architecture (10,000+ concurrent users)
		
		### Authentication
		All endpoints require JWT token except `/auth/*` endpoints.
		
		Get token: `POST /api/v1/auth/login`
		
		Use in header: `Authorization: Bearer <token>`
		
		### Rate Limiting
		- Default: 1000 requests/hour per IP
		- Authentication endpoints: 5 requests/minute
		- Standard endpoints: 100 requests/minute
		
		### Data Isolation
		- **SUPER_ADMIN**: Access to all data
		- **INTERNAL**: Organization-scoped data
		- **EXTERNAL**: Business partner-scoped data
		""",
		docs_url="/api/docs",
		redoc_url="/api/redoc",
		openapi_url="/api/openapi.json",
		contact={
			"name": "Cotton ERP Support",
			"email": "support@cotton-erp.com",
		},
		license_info={
			"name": "Proprietary",
		},
		swagger_ui_parameters={
			"defaultModelsExpandDepth": -1,  # Hide schemas by default
			"persistAuthorization": True,  # Remember auth token
		}
	)
	# Logging config load
	log_cfg_path = Path(__file__).resolve().parents[2] / "configs" / "logging" / "backend.json"
	if log_cfg_path.exists():
		with log_cfg_path.open() as f:
			cfg = json.load(f)
		dictConfig(cfg)
	
	# Enable PII sanitization for production (15-year GDPR compliance)
	if os.getenv("ENABLE_PII_FILTER", "true").lower() == "true":
		try:
			from backend.core.logging.pii_filter import PIIFilter
			
			root_logger = logging.getLogger()
			root_logger.addFilter(PIIFilter())
			print("✓ PII sanitization enabled for all logs")
		except ImportError:
			print("⚠ PII filter not available")
		except Exception as e:
			print(f"⚠ Failed to enable PII filter: {e}")
	# OpenTelemetry instrumentation (GCP-native for 15-year architecture)
	otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	gcp_project_id = os.getenv("GCP_PROJECT_ID")
	
	if gcp_project_id:
		# Production: Use GCP Cloud Trace and Cloud Monitoring
		try:
			from backend.core.observability.gcp import configure_gcp_observability, instrument_application
			
			config = configure_gcp_observability(
				service_name="cotton-erp-backend",
				project_id=gcp_project_id,
				enable_traces=True,
				enable_metrics=True,
			)
			print(f"✓ GCP Observability configured: {config}")
			
			# Auto-instrument (will be done after app creation)
			# instrument_application(app, db_engine)
			
		except ImportError:
			print("⚠ GCP observability libraries not installed")
			print("  Install: pip install opentelemetry-exporter-gcp-trace opentelemetry-exporter-gcp-monitoring")
		except Exception as e:
			print(f"⚠ Failed to configure GCP observability: {e}")
	
	elif otlp_endpoint:
		# Development/Custom: Use OTLP endpoint (original behavior)
		resource = Resource(attributes={"service.name": "cotton-erp-backend"})
		provider = TracerProvider(resource=resource)
		span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
		provider.add_span_processor(BatchSpanProcessor(span_exporter))
		trace.set_tracer_provider(provider)
		FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
	# Middlewares (order matters: RequestID → Idempotency → Auth → Isolation → Security → CORS)
	app.add_middleware(RequestIDMiddleware)
	app.add_middleware(IdempotencyMiddleware)  # Add idempotency BEFORE auth (caching layer)
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

	# Rate limiter with better configuration
	setup_rate_limiting(app)

	# API Routers
	app.include_router(user_onboarding_router, prefix="/api/v1", tags=["auth"])
	app.include_router(partners_router, prefix="/api/v1", tags=["partners"])
	app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])
	
	# Phase 2 Infrastructure Routers
	from backend.api.v1.websocket import router as websocket_router
	from backend.api.v1.webhooks import router as webhooks_router
	# from backend.api.v1.ai import router as ai_router  # Requires langchain, chromadb (optional)
	app.include_router(websocket_router, prefix="/api/v1", tags=["websocket"])
	app.include_router(webhooks_router, prefix="/api/v1", tags=["webhooks"])
	# app.include_router(ai_router, prefix="/api/v1", tags=["ai"])  # Optional: install langchain chromadb
	
	# Session Management (NEW)
	from backend.modules.auth.router import router as session_router
	app.include_router(session_router, prefix="/api/v1", tags=["sessions"])
	
	# Privacy & GDPR (NEW)
	from backend.api.v1.privacy import router as privacy_router
	app.include_router(privacy_router, prefix="/api/v1", tags=["privacy"])
	
	# WebSocket Real-time (NEW)
	from backend.api.v1.websocket import router as websocket_router
	app.include_router(websocket_router, prefix="/api/v1", tags=["websocket"])
	
	# Webhooks (NEW)
	from backend.api.v1.webhooks import router as webhooks_router
	app.include_router(webhooks_router, prefix="/api/v1", tags=["webhooks"])
	
	# Sync API (Mobile Offline-First)
	from backend.api.v1.sync import router as sync_router
	app.include_router(sync_router, prefix="/api/v1", tags=["sync"])
	
	# Risk Management Module (NEW)
	from backend.modules.risk.routes import router as risk_router
	app.include_router(risk_router, prefix="/api/v1", tags=["risk"])
	
	return app


app = create_app()
