"""Notification services"""

from backend.modules.notifications.services.notification_service import (
    NotificationService,
    get_notification_service,
)

__all__ = [
    "NotificationService",
    "get_notification_service",
]
