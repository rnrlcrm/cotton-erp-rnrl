"""
Notification Schemas

Request/Response models for the notification API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.modules.notifications.models import (
    NotificationCategory,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)


# ============== REQUEST SCHEMAS ==============

class SendNotificationRequest(BaseModel):
    """Request to send a notification to a user"""
    
    user_id: UUID = Field(..., description="Recipient user ID")
    type: NotificationType = Field(..., description="Notification type")
    category: NotificationCategory = Field(..., description="Notification category")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Notification priority")
    
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    body: str = Field(..., min_length=1, description="Notification body")
    image_url: Optional[str] = Field(None, max_length=512, description="Optional image URL")
    icon: Optional[str] = Field(None, max_length=50, description="Icon name")
    
    action_url: Optional[str] = Field(None, max_length=512, description="Deep link URL")
    action_label: Optional[str] = Field(None, max_length=100, description="Action button label")
    action_data: Optional[Dict[str, Any]] = Field(None, description="Additional action data")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")


class BulkSendNotificationRequest(BaseModel):
    """Request to send notification to multiple users"""
    
    user_ids: List[UUID] = Field(..., min_items=1, max_items=1000, description="List of recipient user IDs")
    type: NotificationType = Field(..., description="Notification type")
    category: NotificationCategory = Field(..., description="Notification category")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Notification priority")
    
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    body: str = Field(..., min_length=1, description="Notification body")
    image_url: Optional[str] = Field(None, max_length=512, description="Optional image URL")
    icon: Optional[str] = Field(None, max_length=50, description="Icon name")
    
    action_url: Optional[str] = Field(None, max_length=512, description="Deep link URL")
    action_label: Optional[str] = Field(None, max_length=100, description="Action button label")
    action_data: Optional[Dict[str, Any]] = Field(None, description="Additional action data")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")


class MarkAsReadRequest(BaseModel):
    """Request to mark notification(s) as read"""
    
    notification_ids: List[UUID] = Field(..., min_items=1, description="List of notification IDs to mark as read")


class RegisterDeviceTokenRequest(BaseModel):
    """Request to register device token for push notifications"""
    
    device_type: str = Field(..., pattern=r"^(ios|android|web)$", description="Device type")
    device_name: Optional[str] = Field(None, max_length=255, description="Device name")
    device_id: Optional[str] = Field(None, max_length=255, description="Unique device identifier")
    
    fcm_token: Optional[str] = Field(None, max_length=255, description="Firebase Cloud Messaging token")
    apns_token: Optional[str] = Field(None, max_length=255, description="Apple Push Notification Service token")
    web_push_subscription: Optional[Dict[str, Any]] = Field(None, description="Web Push API subscription")


class UpdateNotificationPreferencesRequest(BaseModel):
    """Request to update notification preferences for a category"""
    
    category: NotificationCategory = Field(..., description="Notification category")
    
    push_enabled: bool = Field(True, description="Enable push notifications")
    in_app_enabled: bool = Field(True, description="Enable in-app notifications")
    email_enabled: bool = Field(True, description="Enable email notifications")
    sms_enabled: bool = Field(False, description="Enable SMS notifications")
    websocket_enabled: bool = Field(True, description="Enable WebSocket notifications")
    
    quiet_hours_enabled: bool = Field(False, description="Enable quiet hours")
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="Quiet hours end time (HH:MM)")


# ============== RESPONSE SCHEMAS ==============

class NotificationResponse(BaseModel):
    """Notification response model"""
    
    id: UUID
    user_id: UUID
    organization_id: UUID
    
    type: NotificationType
    category: NotificationCategory
    priority: NotificationPriority
    status: NotificationStatus
    
    title: str
    body: str
    image_url: Optional[str] = None
    icon: Optional[str] = None
    
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated list of notifications"""
    
    total: int = Field(..., description="Total number of notifications")
    unread_count: int = Field(..., description="Number of unread notifications")
    notifications: List[NotificationResponse] = Field(..., description="List of notifications")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="Whether more pages exist")


class NotificationStatsResponse(BaseModel):
    """Notification statistics"""
    
    total_count: int = Field(..., description="Total notifications")
    unread_count: int = Field(..., description="Unread notifications")
    read_count: int = Field(..., description="Read notifications")
    by_category: Dict[str, int] = Field(..., description="Count by category")
    by_priority: Dict[str, int] = Field(..., description="Count by priority")


class DeviceTokenResponse(BaseModel):
    """Device token response"""
    
    id: UUID
    user_id: UUID
    device_type: str
    device_name: Optional[str] = None
    device_id: Optional[str] = None
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationPreferenceResponse(BaseModel):
    """Notification preference response"""
    
    id: UUID
    user_id: UUID
    organization_id: UUID
    category: NotificationCategory
    
    push_enabled: bool
    in_app_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    websocket_enabled: bool
    
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BulkSendResponse(BaseModel):
    """Response for bulk send operation"""
    
    total_sent: int = Field(..., description="Number of notifications sent")
    notification_ids: List[UUID] = Field(..., description="List of created notification IDs")
    failed_user_ids: List[UUID] = Field(default_factory=list, description="List of user IDs that failed")


class MarkAsReadResponse(BaseModel):
    """Response for mark as read operation"""
    
    marked_count: int = Field(..., description="Number of notifications marked as read")
    notification_ids: List[UUID] = Field(..., description="List of notification IDs marked as read")
