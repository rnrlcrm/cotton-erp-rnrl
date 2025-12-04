"""
Notification Models

Database models for the notification system supporting:
- Push notifications (FCM, APNS)
- In-app notifications
- Email notifications
- SMS notifications
- WebSocket real-time delivery
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class NotificationType(str, Enum):
    """Types of notifications"""
    PUSH = "push"  # Mobile push notification (FCM/APNS)
    IN_APP = "in_app"  # In-app notification
    EMAIL = "email"  # Email notification
    SMS = "sms"  # SMS notification
    WEBSOCKET = "websocket"  # Real-time via WebSocket


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"  # Can be batched/delayed
    NORMAL = "normal"  # Standard delivery
    HIGH = "high"  # Immediate delivery
    URGENT = "urgent"  # Critical alerts (bypass quiet hours)


class NotificationCategory(str, Enum):
    """Notification categories for grouping and preferences"""
    TRADE = "trade"  # Trade desk updates (matches, negotiations)
    PARTNER = "partner"  # Partner approvals, KYC updates
    AVAILABILITY = "availability"  # Availability posted/reserved/sold
    REQUIREMENT = "requirement"  # Requirement posted/matched
    PAYMENT = "payment"  # Payment received/pending
    SHIPMENT = "shipment"  # Shipment updates
    COMPLIANCE = "compliance"  # Compliance alerts
    SYSTEM = "system"  # System announcements
    SECURITY = "security"  # Security alerts (login, password change)
    MARKETING = "marketing"  # Promotional messages


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"  # Queued for delivery
    SENT = "sent"  # Successfully sent
    DELIVERED = "delivered"  # Delivered to device/recipient
    READ = "read"  # User opened/read notification
    FAILED = "failed"  # Delivery failed
    CANCELLED = "cancelled"  # Cancelled before delivery


class Notification(Base):
    """
    Core notification model supporting multi-channel delivery.
    
    Features:
    - Multi-channel (push, in-app, email, SMS, WebSocket)
    - Priority-based delivery
    - Rich content (title, body, image, action buttons)
    - Deep linking to app screens
    - Read/unread tracking
    - Delivery status tracking
    - User preferences (per category)
    - Data isolation (organization-scoped)
    """
    
    __tablename__ = "notifications"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Recipient
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Notification metadata
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    category = Column(SQLEnum(NotificationCategory), nullable=False, index=True)
    priority = Column(SQLEnum(NotificationPriority), nullable=False, default=NotificationPriority.NORMAL, index=True)
    status = Column(SQLEnum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING, index=True)
    
    # Content
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    image_url = Column(String(512), nullable=True)  # Optional image
    icon = Column(String(50), nullable=True)  # Icon name (for in-app UI)
    
    # Action/Deep linking
    action_url = Column(String(512), nullable=True)  # Deep link (e.g., "app://trade/123")
    action_label = Column(String(100), nullable=True)  # Button text (e.g., "View Trade")
    action_data = Column(JSON, nullable=True)  # Additional action data
    
    # Delivery tracking
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True, index=True)
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Push notification specific
    fcm_token = Column(String(255), nullable=True)  # Firebase Cloud Messaging token
    apns_token = Column(String(255), nullable=True)  # Apple Push Notification Service token
    push_response = Column(JSON, nullable=True)  # Response from FCM/APNS
    
    # Email specific
    email_address = Column(String(255), nullable=True)
    email_message_id = Column(String(255), nullable=True)  # Message ID from email provider
    
    # SMS specific
    phone_number = Column(String(20), nullable=True)
    sms_message_id = Column(String(255), nullable=True)  # Message ID from SMS provider
    
    # Metadata
    metadata = Column(JSON, nullable=True)  # Additional metadata
    expires_at = Column(DateTime, nullable=True)  # Expiration time (for time-sensitive notifications)
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<Notification {self.id} - {self.title} ({self.status})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "organization_id": str(self.organization_id),
            "type": self.type.value,
            "category": self.category.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "title": self.title,
            "body": self.body,
            "image_url": self.image_url,
            "icon": self.icon,
            "action_url": self.action_url,
            "action_label": self.action_label,
            "action_data": self.action_data,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @property
    def is_read(self) -> bool:
        """Check if notification has been read"""
        return self.read_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Check if notification is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class NotificationPreference(Base):
    """
    User notification preferences per category.
    
    Allows users to control which notifications they receive and how.
    """
    
    __tablename__ = "notification_preferences"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # User
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Category
    category = Column(SQLEnum(NotificationCategory), nullable=False, index=True)
    
    # Channel preferences
    push_enabled = Column(Boolean, nullable=False, default=True)
    in_app_enabled = Column(Boolean, nullable=False, default=True)
    email_enabled = Column(Boolean, nullable=False, default=True)
    sms_enabled = Column(Boolean, nullable=False, default=False)  # SMS off by default
    websocket_enabled = Column(Boolean, nullable=False, default=True)
    
    # Quiet hours
    quiet_hours_enabled = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(String(5), nullable=True)  # e.g., "22:00"
    quiet_hours_end = Column(String(5), nullable=True)  # e.g., "08:00"
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<NotificationPreference {self.user_id} - {self.category}>"


class DeviceToken(Base):
    """
    Device tokens for push notifications (FCM/APNS).
    
    Supports multiple devices per user (mobile, tablet, etc.)
    """
    
    __tablename__ = "device_tokens"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # User
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Device info
    device_type = Column(String(20), nullable=False)  # ios, android, web
    device_name = Column(String(255), nullable=True)  # iPhone 13, Pixel 6, etc.
    device_id = Column(String(255), nullable=True, index=True)  # Unique device identifier
    
    # Tokens
    fcm_token = Column(String(255), nullable=True, unique=True, index=True)  # Firebase token
    apns_token = Column(String(255), nullable=True, unique=True, index=True)  # Apple token
    web_push_subscription = Column(JSON, nullable=True)  # Web Push API subscription
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<DeviceToken {self.device_type} - {self.device_name}>"
