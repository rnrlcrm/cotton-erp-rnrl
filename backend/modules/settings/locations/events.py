"""
Location Module Events

Events emitted for location lifecycle actions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class LocationEventData(BaseModel):
    """Base event data for location events"""
    location_id: UUID
    name: str
    google_place_id: str
    city: Optional[str]
    state: Optional[str]
    region: Optional[str]
    is_active: bool


class LocationCreatedEvent(BaseModel):
    """Event emitted when a location is created"""
    event_type: str = "location.created"
    aggregate_id: UUID
    aggregate_type: str = "location"
    user_id: UUID
    timestamp: datetime
    version: int = 1
    data: LocationEventData
    metadata: Optional[dict] = None


class LocationUpdatedEvent(BaseModel):
    """Event emitted when a location is updated"""
    event_type: str = "location.updated"
    aggregate_id: UUID
    aggregate_type: str = "location"
    user_id: UUID
    timestamp: datetime
    version: int = 1
    data: dict  # Contains before/after changes
    metadata: Optional[dict] = None


class LocationDeletedEvent(BaseModel):
    """Event emitted when a location is soft deleted"""
    event_type: str = "location.deleted"
    aggregate_id: UUID
    aggregate_type: str = "location"
    user_id: UUID
    timestamp: datetime
    version: int = 1
    data: dict  # Contains location_id and name
    metadata: Optional[dict] = None
