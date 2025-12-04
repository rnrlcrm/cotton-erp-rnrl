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
from backend.db.async_session import async_engine
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.core.errors.exceptions import DomainError
from backend.app.middleware.rate_limit import setup_rate_limiting


def create_app() -> FastAPI:
	app = FastAPI(
		title="Commodity ERP API",
		version="1.0.0",
		description="""
		## 2035-Ready Commodity Trading ERP System
		
		Complete ERP system for commodity trading with:
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
			"name": "Multi-Commodity ERP Support",
			"email": "support@commodity-erp.com",
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
	# OpenTelemetry instrumentation (GCP-native for production)
	otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	gcp_project_id = os.getenv("GCP_PROJECT_ID")
	enable_tracing = os.getenv("ENABLE_TRACING", "false").lower() == "true"
	
	if enable_tracing:
		if gcp_project_id:
			# Production: Use GCP Cloud Trace and Cloud Monitoring
			try:
				from backend.core.observability.gcp import configure_gcp_observability, instrument_application
				
				config = configure_gcp_observability(
					service_name="commodity-erp-backend",
					project_id=gcp_project_id,
					enable_traces=True,
					enable_metrics=True,
				)
				print(f"✓ GCP Observability configured: {config}")
				
				# Instrument app after creation
				instrument_application(app, async_engine)
				
			except ImportError:
				print("⚠ GCP observability libraries not installed")
				print("  Install: pip install opentelemetry-exporter-gcp-trace opentelemetry-exporter-gcp-monitoring")
			except Exception as e:
				print(f"⚠ Failed to configure GCP observability: {e}")
		
		elif otlp_endpoint:
			# Development/Custom: Use OTLP endpoint
			try:
				resource = Resource(attributes={
					"service.name": "commodity-erp-backend",
					"service.version": "1.0.0",
					"deployment.environment": os.getenv("ENV", "development")
				})
				provider = TracerProvider(resource=resource)
				span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
				provider.add_span_processor(BatchSpanProcessor(span_exporter))
				trace.set_tracer_provider(provider)
				FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
				print(f"✓ OpenTelemetry tracing enabled: {otlp_endpoint}")
			except Exception as e:
				print(f"⚠ Failed to configure OpenTelemetry: {e}")
		else:
			print("ℹ Tracing enabled but no endpoint configured (set OTEL_EXPORTER_OTLP_ENDPOINT or GCP_PROJECT_ID)")
	else:
		print("ℹ OpenTelemetry tracing disabled (set ENABLE_TRACING=true to enable)")
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
	async def readiness() -> dict:
		try:
			async with async_engine.connect() as conn:
				await conn.execute(text("SELECT 1"))
			return {"ready": True}
		except Exception:
			return {"ready": False}

	# Rate limiter with better configuration
	setup_rate_limiting(app)

	# API Routers
	app.include_router(user_onboarding_router, prefix="/api/v1", tags=["auth"])
	app.include_router(partners_router, prefix="/api/v1", tags=["partners"])
	app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])
	
	# Infrastructure Routers (Single Registration)
	from backend.api.v1.websocket import router as websocket_router
	from backend.api.v1.webhooks import router as webhooks_router
	from backend.api.v1.sync import router as sync_router
	from backend.api.v1.privacy import router as privacy_router
	from backend.modules.auth.router import router as session_router
	from backend.modules.risk.routes import router as risk_router
	# from backend.modules.capabilities.router import router as capabilities_router  # FIXME: Has import errors
	from backend.modules.trade_desk.routes.availability_routes import router as availability_router
	from backend.modules.trade_desk.routes.requirement_routes import router as requirement_router
	from backend.modules.trade_desk.routes.matching_router import router as matching_router
	from backend.modules.trade_desk.routes.negotiation_routes import router as negotiation_router
	from backend.modules.trade_desk.routes.negotiation_routes import admin_router as negotiation_admin_router
	from backend.modules.notifications.routes import router as notifications_router
	
	app.include_router(websocket_router, prefix="/api/v1", tags=["websocket"])
	app.include_router(webhooks_router, prefix="/api/v1", tags=["webhooks"])
	app.include_router(sync_router, prefix="/api/v1", tags=["sync"])
	app.include_router(privacy_router, prefix="/api/v1", tags=["privacy"])
	app.include_router(session_router, prefix="/api/v1", tags=["sessions"])
	app.include_router(risk_router, prefix="/api/v1", tags=["risk"])
	# app.include_router(capabilities_router, prefix="/api/v1", tags=["capabilities"])  # FIXME: Has import errors
	app.include_router(notifications_router, prefix="/api/v1", tags=["notifications"])
	app.include_router(availability_router, prefix="/api/v1/trade-desk", tags=["trade-desk"])
	app.include_router(requirement_router, prefix="/api/v1/trade-desk", tags=["trade-desk"])
	app.include_router(matching_router, prefix="/api/v1/trade-desk", tags=["trade-desk"])
	app.include_router(negotiation_router, prefix="/api/v1/trade-desk", tags=["trade-desk"])
	app.include_router(negotiation_admin_router, prefix="/api/v1/trade-desk", tags=["trade-desk-admin"])
	
	# AI Infrastructure Startup
	@app.on_event("startup")
	async def startup_ai_services():
		"""Initialize AI services on application startup."""
		try:
			from backend.ai.startup import initialize_ai_services
			from backend.db.async_session import get_db
			
			# Get database session
			db = await anext(get_db())
			
			# Initialize AI services (vector sync, guardrails, memory)
			# Note: EventBus subscription not yet implemented, passing None
			await initialize_ai_services(db, redis=None, event_bus=None)
			
			print("✅ AI services initialized successfully")
		except Exception as e:
			print(f"⚠️  Failed to initialize AI services: {e}")
			import traceback
			traceback.print_exc()
			# Don't fail app startup if AI initialization fails
	
	return app


app = create_app()
