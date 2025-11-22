from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

# Configure an audit logger if not already configured by global logging setup.
logger = logging.getLogger("audit")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")  # JSON already formatted below
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Context var populated by request-id middleware
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def audit_log(
    action: str,
    user_id: Any | None,
    entity: str,
    entity_id: Any | None,
    details: dict | None = None,
    correlation_id: str | None = None,
) -> str:
    """Emit a structured audit record.

    Returns the correlation_id used so callers can chain additional events.
    """
    if correlation_id is None:
        correlation_id = str(uuid4())
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
        "action": action,
        "user_id": user_id,
        "entity": entity,
        "entity_id": entity_id,
        "details": details or {},
    }
    rid = request_id_ctx.get()
    if rid:
        payload["request_id"] = rid
    logger.info(json.dumps(payload), extra={"audit": True, "action": action})
    return correlation_id


# === Data Isolation & Compliance Audit Functions ===
# Added for GDPR Article 30 (Records of Processing Activities)
# IT Act 2000 Section 43A (Audit Trail)
# Income Tax Act 1961 (Transaction Audit)


def log_data_access(
    user_id: Any,
    user_type: str,
    business_partner_id: Any | None,
    path: str,
    method: str,
    ip_address: str,
    user_agent: str = "",
) -> None:
    """
    Log all API data access for compliance.
    
    GDPR Article 30: Records of Processing Activities
    IT Act 2000: Audit trail requirement
    
    Args:
        user_id: User's unique identifier
        user_type: SUPER_ADMIN, INTERNAL, or EXTERNAL
        business_partner_id: Business partner ID (for EXTERNAL users)
        path: API path accessed
        method: HTTP method (GET, POST, etc.)
        ip_address: Client IP address
        user_agent: User agent string
    """
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "data_access",
        "user_id": user_id,
        "user_type": user_type,
        "business_partner_id": business_partner_id,
        "path": path,
        "method": method,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
    rid = request_id_ctx.get()
    if rid:
        payload["request_id"] = rid
    
    logger.info(json.dumps(payload), extra={"audit": True, "action": "data_access"})


def log_data_export(
    user_id: Any,
    business_partner_id: Any,
    export_type: str,
    record_count: int,
    file_format: str = "json",
) -> None:
    """
    Log data export events.
    
    GDPR Article 20: Right to Data Portability
    Required for compliance auditing.
    
    Args:
        user_id: User who requested export
        business_partner_id: Business partner whose data was exported
        export_type: Type of data (contracts, invoices, etc.)
        record_count: Number of records exported
        file_format: Export format (json, csv, pdf)
    """
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "data_export",
        "user_id": user_id,
        "business_partner_id": business_partner_id,
        "export_type": export_type,
        "record_count": record_count,
        "file_format": file_format,
    }
    rid = request_id_ctx.get()
    if rid:
        payload["request_id"] = rid
    
    logger.warning(json.dumps(payload), extra={"audit": True, "action": "data_export"})


def log_data_deletion(
    user_id: Any,
    business_partner_id: Any,
    deletion_type: str,
    entity: str,
    entity_id: Any,
    reason: str,
    is_hard_delete: bool = False,
) -> None:
    """
    Log data deletion events (soft or hard delete).
    
    GDPR Article 17: Right to Erasure
    Income Tax Act: Must log before deletion (7-year retention)
    
    Args:
        user_id: User who performed deletion
        business_partner_id: Business partner whose data was deleted
        deletion_type: Type of deletion (soft, hard, gdpr_erasure)
        entity: Entity type (contract, invoice, etc.)
        entity_id: Entity's unique ID
        reason: Reason for deletion
        is_hard_delete: Whether this is permanent deletion
    """
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "data_deletion",
        "user_id": user_id,
        "business_partner_id": business_partner_id,
        "deletion_type": deletion_type,
        "entity": entity,
        "entity_id": entity_id,
        "reason": reason,
        "is_hard_delete": is_hard_delete,
    }
    rid = request_id_ctx.get()
    if rid:
        payload["request_id"] = rid
    
    # Use ERROR level for hard deletes (permanent)
    log_level = logger.error if is_hard_delete else logger.warning
    log_level(json.dumps(payload), extra={"audit": True, "action": "data_deletion"})


def log_cross_branch_invoice(
    user_id: Any,
    invoice_id: Any,
    branch_id: Any,
    business_partner_id: Any,
) -> None:
    """
    Log when back-office creates invoice in different branch.
    
    Income Tax Act: Track which branch issued invoice
    GST Act: Branch-wise invoice tracking
    
    Args:
        user_id: Internal user who created invoice
        invoice_id: Invoice unique ID
        branch_id: Branch (GST unit) that issued invoice
        business_partner_id: Business partner for whom invoice was created
    """
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "cross_branch_invoice",
        "user_id": user_id,
        "invoice_id": invoice_id,
        "branch_id": branch_id,
        "business_partner_id": business_partner_id,
    }
    rid = request_id_ctx.get()
    if rid:
        payload["request_id"] = rid
    
    logger.info(json.dumps(payload), extra={"audit": True, "action": "cross_branch_invoice"})


def log_isolation_violation(
    user_id: Any,
    user_type: str,
    attempted_resource: str,
    attempted_business_partner_id: Any,
    user_business_partner_id: Any | None,
    reason: str,
) -> None:
    """
    Log attempted data isolation violation (security incident).
    
    IT Act 2000: Security breach logging
    
    Args:
        user_id: User who attempted access
        user_type: User's type
        attempted_resource: Resource they tried to access
        attempted_business_partner_id: BP they tried to access
        user_business_partner_id: Their actual BP
        reason: Why violation was detected
    """
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "isolation_violation",
        "severity": "HIGH",
        "user_id": user_id,
        "user_type": user_type,
        "attempted_resource": attempted_resource,
        "attempted_business_partner_id": attempted_business_partner_id,
        "user_business_partner_id": user_business_partner_id,
        "reason": reason,
    }
    rid = request_id_ctx.get()
    if rid:
        payload["request_id"] = rid
    
    logger.error(json.dumps(payload), extra={"audit": True, "action": "isolation_violation"})

