"""Notification schemas"""

from backend.modules.notifications.schemas.notification_schemas import (
    BulkSendNotificationRequest,
    BulkSendResponse,
    DeviceTokenResponse,
    MarkAsReadRequest,
    MarkAsReadResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationResponse,
    NotificationStatsResponse,
    RegisterDeviceTokenRequest,
    SendNotificationRequest,
    UpdateNotificationPreferencesRequest,
)

__all__ = [
    "SendNotificationRequest",
    "BulkSendNotificationRequest",
    "MarkAsReadRequest",
    "RegisterDeviceTokenRequest",
    "UpdateNotificationPreferencesRequest",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationStatsResponse",
    "DeviceTokenResponse",
    "NotificationPreferenceResponse",
    "BulkSendResponse",
    "MarkAsReadResponse",
]
