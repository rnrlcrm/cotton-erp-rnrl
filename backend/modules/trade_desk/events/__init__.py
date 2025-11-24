"""
Trade Desk Events

Domain events for Trade Desk module - supports event sourcing and real-time updates.
"""

from backend.modules.trade_desk.events.availability_events import (
    AvailabilityCreatedEvent,
    AvailabilityUpdatedEvent,
    AvailabilityVisibilityChangedEvent,
    AvailabilityPriceChangedEvent,
    AvailabilityQuantityChangedEvent,
    AvailabilityReservedEvent,
    AvailabilityReleasedEvent,
    AvailabilitySoldEvent,
    AvailabilityExpiredEvent,
    AvailabilityCancelledEvent,
)

__all__ = [
    # Availability Events
    "AvailabilityCreatedEvent",
    "AvailabilityUpdatedEvent",
    "AvailabilityVisibilityChangedEvent",
    "AvailabilityPriceChangedEvent",
    "AvailabilityQuantityChangedEvent",
    "AvailabilityReservedEvent",
    "AvailabilityReleasedEvent",
    "AvailabilitySoldEvent",
    "AvailabilityExpiredEvent",
    "AvailabilityCancelledEvent",
]
