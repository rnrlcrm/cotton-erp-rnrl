"""
Location Module

Master location registry for the entire Cotton ERP system.
All location data sourced from Google Maps API.

Exports:
- models: Location
- schemas: LocationCreate, LocationUpdate, LocationResponse, etc.
- router: API router
"""

from backend.modules.settings.locations.models import Location
from backend.modules.settings.locations.router import router
from backend.modules.settings.locations.schemas import (
    LocationCreate,
    LocationListResponse,
    LocationResponse,
    LocationUpdate,
)

__all__ = [
    "Location",
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    "LocationListResponse",
    "router",
]
