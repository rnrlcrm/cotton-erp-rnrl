"""
OpenTelemetry Configuration for Google Cloud Platform

Configures OpenTelemetry to export to GCP Cloud Trace and Cloud Monitoring.
NO business logic changes - pure observability infrastructure.

Features for 15-year architecture:
- Distributed tracing across all services
- Automatic metric collection
- GCP-native integration
- Correlation with logs via trace_id
"""

import os
from typing import Optional
import logging

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

logger = logging.getLogger(__name__)


def configure_gcp_observability(
    service_name: str = "cotton-erp-backend",
    project_id: Optional[str] = None,
    enable_traces: bool = True,
    enable_metrics: bool = True,
) -> dict:
    """
    Configure OpenTelemetry for GCP Cloud Trace and Cloud Monitoring.
    
    This function sets up the global tracer and meter providers.
    Call ONCE at application startup.
    
    Args:
        service_name: Name of the service (for filtering in GCP)
        project_id: GCP project ID (defaults to env var)
        enable_traces: Whether to export traces to Cloud Trace
        enable_metrics: Whether to export metrics to Cloud Monitoring
        
    Returns:
        Configuration info dictionary
        
    Example:
        ```python
        # In main.py
        from backend.core.observability.gcp import configure_gcp_observability
        
        configure_gcp_observability(
            service_name="cotton-erp-backend",
            project_id="cotton-erp-prod"
        )
        ```
    """
    if project_id is None:
        project_id = os.getenv("GCP_PROJECT_ID", "")
    
    # Create resource (service identification)
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("APP_VERSION", "1.0.0"),
        "deployment.environment": os.getenv("ENV", "dev"),
        "cloud.provider": "gcp",
        "cloud.platform": "gcp_cloud_run",
    })
    
    config_info = {
        "service_name": service_name,
        "project_id": project_id,
        "traces_enabled": False,
        "metrics_enabled": False,
    }
    
    # Configure Traces
    if enable_traces and project_id:
        try:
            # Create tracer provider
            tracer_provider = TracerProvider(resource=resource)
            
            # Add Cloud Trace exporter
            cloud_trace_exporter = CloudTraceSpanExporter(project_id=project_id)
            span_processor = BatchSpanProcessor(cloud_trace_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(tracer_provider)
            
            config_info["traces_enabled"] = True
            logger.info(f"✓ Cloud Trace configured for project: {project_id}")
            
        except Exception as e:
            logger.warning(f"Failed to configure Cloud Trace: {e}")
    
    # Configure Metrics
    if enable_metrics and project_id:
        try:
            # Create metrics exporter
            cloud_monitoring_exporter = CloudMonitoringMetricsExporter(
                project_id=project_id
            )
            
            # Create metric reader (exports every 60 seconds)
            metric_reader = PeriodicExportingMetricReader(
                cloud_monitoring_exporter,
                export_interval_millis=60000,  # 1 minute
            )
            
            # Create meter provider
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader],
            )
            
            # Set global meter provider
            metrics.set_meter_provider(meter_provider)
            
            config_info["metrics_enabled"] = True
            logger.info(f"✓ Cloud Monitoring configured for project: {project_id}")
            
        except Exception as e:
            logger.warning(f"Failed to configure Cloud Monitoring: {e}")
    
    return config_info


def instrument_application(app=None, db_engine=None):
    """
    Auto-instrument common libraries.
    
    This adds tracing to:
    - FastAPI endpoints (automatic spans)
    - SQLAlchemy queries (database traces)
    - Redis operations
    - HTTP requests
    
    Args:
        app: FastAPI application (optional)
        db_engine: SQLAlchemy engine (optional)
    """
    try:
        # Instrument FastAPI
        if app:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("✓ FastAPI instrumented")
        
        # Instrument SQLAlchemy
        if db_engine:
            SQLAlchemyInstrumentor().instrument(engine=db_engine)
            logger.info("✓ SQLAlchemy instrumented")
        
        # Instrument Redis
        RedisInstrumentor().instrument()
        logger.info("✓ Redis instrumented")
        
        # Instrument HTTP requests
        RequestsInstrumentor().instrument()
        logger.info("✓ HTTP requests instrumented")
        
    except Exception as e:
        logger.warning(f"Failed to instrument application: {e}")


# Custom metrics for business logic
def get_business_metrics():
    """
    Get meter for custom business metrics.
    
    Use this to track business-specific metrics like:
    - Trade execution count
    - Match success rate
    - Partner onboarding time
    
    Example:
        ```python
        from backend.core.observability.gcp import get_business_metrics
        
        meter = get_business_metrics()
        trade_counter = meter.create_counter(
            "trades.executed",
            description="Number of trades executed",
            unit="1",
        )
        
        # Later, in business logic:
        trade_counter.add(1, {"status": "success", "partner_type": "buyer"})
        ```
    """
    return metrics.get_meter("cotton_erp.business")


# SLO Definitions (for alerting)
SLO_DEFINITIONS = {
    "api_availability": {
        "description": "API should be available 99.9% of the time",
        "target": 0.999,
        "measurement": "successful_requests / total_requests",
        "window": "30d",
    },
    "api_latency_p99": {
        "description": "99% of API requests should complete within 2 seconds",
        "target": 2000,  # milliseconds
        "measurement": "request_duration_p99",
        "window": "5m",
    },
    "database_latency_p99": {
        "description": "99% of database queries should complete within 100ms",
        "target": 100,  # milliseconds
        "measurement": "db_query_duration_p99",
        "window": "5m",
    },
    "matching_success_rate": {
        "description": "Matching engine should succeed 95% of the time",
        "target": 0.95,
        "measurement": "successful_matches / total_match_attempts",
        "window": "1h",
    },
}


def create_slo_alerts(project_id: str):
    """
    Create SLO-based alerts in GCP Monitoring.
    
    This is typically run once during deployment setup.
    
    Args:
        project_id: GCP project ID
    """
    try:
        from google.cloud import monitoring_v3
        
        client = monitoring_v3.AlertPolicyServiceClient()
        project_name = f"projects/{project_id}"
        
        # Create alert for API availability
        alert_policy = monitoring_v3.AlertPolicy(
            display_name="API Availability SLO Breach",
            conditions=[
                monitoring_v3.AlertPolicy.Condition(
                    display_name="API availability < 99.9%",
                    condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                        filter='metric.type="custom.googleapis.com/cotton_erp/api/availability"',
                        comparison=monitoring_v3.ComparisonType.COMPARISON_LT,
                        threshold_value=0.999,
                        duration={"seconds": 300},
                    ),
                )
            ],
            notification_channels=[],  # Add your notification channels
            alert_strategy=monitoring_v3.AlertPolicy.AlertStrategy(
                auto_close={"seconds": 3600}  # Auto-close after 1 hour
            ),
        )
        
        client.create_alert_policy(name=project_name, alert_policy=alert_policy)
        logger.info("✓ SLO alerts created")
        
    except Exception as e:
        logger.warning(f"Failed to create SLO alerts: {e}")


# Structured logging with trace correlation
def get_trace_context():
    """
    Get current trace context for log correlation.
    
    Use this to add trace_id to logs so they appear in Cloud Trace.
    
    Returns:
        Dictionary with trace_id and span_id
        
    Example:
        ```python
        import logging
        from backend.core.observability.gcp import get_trace_context
        
        logger = logging.getLogger(__name__)
        trace_ctx = get_trace_context()
        logger.info("Processing trade", extra=trace_ctx)
        ```
    """
    span = trace.get_current_span()
    span_context = span.get_span_context()
    
    if span_context and span_context.is_valid:
        return {
            "trace_id": format(span_context.trace_id, "032x"),
            "span_id": format(span_context.span_id, "016x"),
            "trace_sampled": span_context.trace_flags.sampled,
        }
    
    return {}
