"""
Capability-Based Authorization Framework

Implements fine-grained authorization using capabilities instead of simple role-based access.

Traditional RBAC Problem:
- Roles are too coarse-grained (e.g., "Admin" can do EVERYTHING)
- Hard to implement principle of least privilege
- Difficult to audit who can do what

Capability-Based Solution:
- Each operation requires specific capabilities
- Users/Roles are assigned capabilities
- Easy to audit and revoke specific permissions
- Supports temporal capabilities (expire after X days)
- Supports conditional capabilities (only in certain contexts)

Example Capabilities:
- AVAILABILITY_CREATE
- AVAILABILITY_APPROVE
- REQUIREMENT_CREATE
- REQUIREMENT_AI_ADJUST
- ORGANIZATION_CREATE
- PARTNER_ONBOARD
- COMMODITY_UPDATE_PRICE
- MATCHING_EXECUTE
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.session import Base


class CapabilityCategory(str, enum.Enum):
    """Categories of capabilities for organization"""
    AUTH = "auth"
    ORGANIZATION = "organization"
    PARTNER = "partner"
    COMMODITY = "commodity"
    LOCATION = "location"
    AVAILABILITY = "availability"
    REQUIREMENT = "requirement"
    MATCHING = "matching"
    ADMIN = "admin"
    SYSTEM = "system"


class Capability(Base):
    """
    Capability Definition
    
    Defines all available capabilities in the system.
    Capabilities are created by migrations, not at runtime.
    """
    
    __tablename__ = "capabilities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Capability identification
    code = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "AVAILABILITY_CREATE"
    name = Column(String(200), nullable=False)  # e.g., "Create Availability"
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True)  # From CapabilityCategory enum
    
    # Metadata
    is_system = Column(Boolean, nullable=False, default=False)  # System capabilities cannot be deleted
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))
    
    # Relationships
    user_capabilities = relationship("UserCapability", back_populates="capability", cascade="all, delete-orphan")
    role_capabilities = relationship("RoleCapability", back_populates="capability", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Capability(code={self.code}, name={self.name})>"


class UserCapability(Base):
    """
    User-Specific Capability Assignment
    
    Directly assign capabilities to individual users.
    Useful for:
    - Temporary elevated permissions
    - Special cases that don't fit roles
    - Emergency access grants
    """
    
    __tablename__ = "user_capabilities"
    __table_args__ = (
        UniqueConstraint('user_id', 'capability_id', name='uq_user_capability'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    capability_id = Column(UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Temporal capabilities (optional expiration)
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    reason = Column(Text, nullable=True)  # Why was this capability granted?
    
    # Relationships
    capability = relationship("Capability", back_populates="user_capabilities")
    
    @property
    def is_active(self) -> bool:
        """Check if capability is currently active"""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def __repr__(self):
        return f"<UserCapability(user_id={self.user_id}, capability_id={self.capability_id})>"


class RoleCapability(Base):
    """
    Role-Based Capability Assignment
    
    Assign capabilities to roles. Users inherit all capabilities
    from their assigned roles.
    """
    
    __tablename__ = "role_capabilities"
    __table_args__ = (
        UniqueConstraint('role_id', 'capability_id', name='uq_role_capability'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    capability_id = Column(UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Audit
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    capability = relationship("Capability", back_populates="role_capabilities")
    
    def __repr__(self):
        return f"<RoleCapability(role_id={self.role_id}, capability_id={self.capability_id})>"
