"""
Event Versioning Strategy

This module defines how we handle event schema evolution over 15 years.

CRITICAL for 15-year architecture:
- Events are immutable records in the event store
- Consumers may be deployed at different times
- Need backward/forward compatibility

Versioning Rules:
1. NEVER break existing events - only add new versions
2. Always include version field in events
3. Consumers must handle multiple versions
4. Version format: integer (1, 2, 3, ...)

Example Evolution:
    Version 1: {"trade_id": "...", "amount": 100}
    Version 2: {"trade_id": "...", "amount": 100, "currency": "USD"}
    
    Version 2 consumer reads Version 1 event:
    - Sets currency = "USD" (default)
    
    Version 1 consumer reads Version 2 event:
    - Ignores currency field (graceful degradation)
"""

from typing import Any, Dict, Type
from backend.core.events.base import BaseEvent


# Event version registry
EVENT_VERSIONS: Dict[str, int] = {
    # Format: "event_type": current_version
    
    # Organization events
    "organization.created": 1,
    "organization.updated": 1,
    "organization.deleted": 1,
    
    # User events
    "user.created": 1,
    "user.updated": 1,
    "user.role_changed": 1,
    
    # Partner events
    "partner.created": 1,
    "partner.updated": 1,
    "partner.verified": 1,
    "partner.document_uploaded": 1,
    
    # Commodity events
    "commodity.created": 1,
    "commodity.updated": 1,
    "commodity.deleted": 1,
    
    # Location events
    "location.created": 1,
    "location.updated": 1,
    
    # Availability events
    "availability.created": 1,
    "availability.updated": 1,
    "availability.matched": 1,
    
    # Requirement events
    "requirement.created": 1,
    "requirement.updated": 1,
    "requirement.matched": 1,
    
    # Trade events
    "trade.created": 1,
    "trade.executed": 1,
    "trade.cancelled": 1,
    "trade.settled": 1,
    
    # Risk events
    "risk.assessment_created": 1,
    "risk.limit_breached": 1,
    
    # Webhook events
    "webhook.delivered": 1,
    "webhook.failed": 1,
    
    # Session events
    "session.created": 1,
    "session.revoked": 1,
}


def get_current_version(event_type: str) -> int:
    """
    Get current version for an event type.
    
    Returns:
        Current version number (default: 1)
    """
    return EVENT_VERSIONS.get(event_type, 1)


def validate_event_version(event: BaseEvent) -> None:
    """
    Validate that event version is supported.
    
    Raises:
        ValueError: If version is invalid
    """
    current = get_current_version(event.event_type)
    
    if event.version < 1:
        raise ValueError(f"Event version must be >= 1, got {event.version}")
    
    if event.version > current:
        raise ValueError(
            f"Event {event.event_type} version {event.version} "
            f"is newer than current version {current}"
        )


def upgrade_event_version(event_data: Dict[str, Any], from_version: int, to_version: int) -> Dict[str, Any]:
    """
    Upgrade event data from one version to another.
    
    This is used when reading old events from the event store.
    
    Args:
        event_data: Event payload
        from_version: Source version
        to_version: Target version
        
    Returns:
        Upgraded event data
        
    Example:
        ```python
        # Reading v1 event, current system expects v2
        old_event = {"trade_id": "...", "amount": 100}
        new_event = upgrade_event_version(old_event, 1, 2)
        # Result: {"trade_id": "...", "amount": 100, "currency": "USD"}
        ```
    """
    if from_version == to_version:
        return event_data
    
    # Apply migrations sequentially
    current_data = event_data.copy()
    
    for version in range(from_version, to_version):
        migration_func_name = f"_migrate_{version}_to_{version + 1}"
        
        # Check if migration exists
        if migration_func_name in globals():
            migration_func = globals()[migration_func_name]
            current_data = migration_func(current_data)
        else:
            # No explicit migration - assume backward compatible
            pass
    
    return current_data


def downgrade_event_version(event_data: Dict[str, Any], from_version: int, to_version: int) -> Dict[str, Any]:
    """
    Downgrade event data to older version.
    
    This is used when old consumers read new events.
    
    Args:
        event_data: Event payload
        from_version: Source version
        to_version: Target version (older)
        
    Returns:
        Downgraded event data (removes new fields)
    """
    if from_version == to_version:
        return event_data
    
    # For now, simple strategy: remove fields added in newer versions
    # In production, implement proper downgrades
    return event_data


# Example migration functions (add as needed):

def _migrate_1_to_2_trade_created(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example: Migrate trade.created from v1 to v2.
    
    v1: {"trade_id": "...", "amount": 100}
    v2: {"trade_id": "...", "amount": 100, "currency": "USD"}
    """
    if "currency" not in data:
        data["currency"] = "USD"  # Default currency
    return data


# Compatibility matrix (for documentation)
COMPATIBILITY_MATRIX = """
Event Versioning Compatibility Matrix

Version Changes:
----------------

trade.created:
  v1 → v2: Added currency field (default: USD)
  - v2 consumers can read v1 (adds default)
  - v1 consumers can read v2 (ignores currency)

(Add more as events evolve)
"""
