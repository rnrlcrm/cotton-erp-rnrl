"""
Location Module Models

Master location registry for the entire system.
All location data sourced from Google Maps API only.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.db.session import Base


class Location(Base):
    """
    Location Master Table
    
    Single source of truth for all locations across the system.
    Data fetched exclusively from Google Maps API.
    Used by: Organizations, Users, Buyers, Sellers, Transporters, Trade Desk, etc.
    """
    
    __tablename__ = "settings_locations"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core Fields
    name = Column(String(255), nullable=False, index=True)
    google_place_id = Column(String(255), nullable=False, unique=True, index=True)  # Prevents duplicates
    
    # Address Details (from Google Maps)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Location Breakdown (from Google Maps)
    pincode = Column(String(20), nullable=True, index=True)
    city = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True, index=True)
    state_code = Column(String(10), nullable=True)  # MH, GJ, TN, etc.
    country = Column(String(100), nullable=True)
    
    # Auto-calculated Region
    region = Column(String(50), nullable=True, index=True)  # WEST, SOUTH, NORTH, CENTRAL, EAST, NORTHEAST
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), nullable=True)  # Reference to users table (no FK for now)
    updated_by = Column(UUID(as_uuid=True), nullable=True)  # Reference to users table (no FK for now)
    
    # Indexes
    __table_args__ = (
        Index('ix_settings_locations_google_place_id', 'google_place_id'),
        Index('ix_settings_locations_city', 'city'),
        Index('ix_settings_locations_state', 'state'),
        Index('ix_settings_locations_pincode', 'pincode'),
        Index('ix_settings_locations_region', 'region'),
        Index('ix_settings_locations_is_active', 'is_active'),
    )
    
    def __repr__(self) -> str:
        return f"<Location(id={self.id}, name={self.name}, city={self.city}, state={self.state})>"
