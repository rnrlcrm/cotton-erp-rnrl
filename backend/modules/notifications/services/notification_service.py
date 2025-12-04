"""
Notification Service

Business logic for sending and managing notifications.

Supports:
- Push notifications (FCM for Android, APNS for iOS)
- In-app notifications
- Email notifications
- SMS notifications
- WebSocket real-time delivery
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.notifications.models import (
    DeviceToken,
    Notification,
    NotificationCategory,
    NotificationPreference,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from backend.modules.notifications.repositories import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending and managing notifications.
    
    Features:
    - Multi-channel delivery
    - User preferences
    - Quiet hours
    - Priority-based routing
    - Delivery tracking
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)
    
    async def send_notification(
        self,
        user_id: UUID,
        organization_id: UUID,
        notification_type: NotificationType,
        category: NotificationCategory,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        image_url: Optional[str] = None,
        icon: Optional[str] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> Notification:
        """
        Send a notification to a user.
        
        Steps:
        1. Check user preferences
        2. Create notification record
        3. Send via appropriate channel(s)
        4. Track delivery status
        """
        # Get user preferences for this category
        preferences = await self.repo.get_preference(
            user_id=user_id,
            organization_id=organization_id,
            category=category
        )
        
        # Check if user has disabled this type of notification
        if preferences:
            should_send = self._should_send_notification(
                notification_type=notification_type,
                preferences=preferences,
                priority=priority
            )
            if not should_send:
                logger.info(f"Notification blocked by user preferences: user={user_id}, category={category}")
                # Still create record but mark as cancelled
                notification = await self._create_notification_record(
                    user_id=user_id,
                    organization_id=organization_id,
                    notification_type=notification_type,
                    category=category,
                    title=title,
                    body=body,
                    priority=priority,
                    image_url=image_url,
                    icon=icon,
                    action_url=action_url,
                    action_label=action_label,
                    action_data=action_data,
                    metadata=metadata,
                    expires_at=expires_at,
                    status=NotificationStatus.CANCELLED
                )
                return notification
        
        # Create notification record
        notification = await self._create_notification_record(
            user_id=user_id,
            organization_id=organization_id,
            notification_type=notification_type,
            category=category,
            title=title,
            body=body,
            priority=priority,
            image_url=image_url,
            icon=icon,
            action_url=action_url,
            action_label=action_label,
            action_data=action_data,
            metadata=metadata,
            expires_at=expires_at,
        )
        
        # Send via appropriate channel
        try:
            if notification_type == NotificationType.PUSH:
                await self._send_push_notification(notification)
            elif notification_type == NotificationType.IN_APP:
                # In-app notifications are already stored in DB
                await self.repo.update_status(
                    notification_id=notification.id,
                    status=NotificationStatus.SENT,
                    sent_at=datetime.utcnow()
                )
            elif notification_type == NotificationType.EMAIL:
                await self._send_email_notification(notification)
            elif notification_type == NotificationType.SMS:
                await self._send_sms_notification(notification)
            elif notification_type == NotificationType.WEBSOCKET:
                await self._send_websocket_notification(notification)
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to send notification {notification.id}: {e}")
            await self.repo.update_status(
                notification_id=notification.id,
                status=NotificationStatus.FAILED,
                failed_at=datetime.utcnow(),
                failure_reason=str(e)
            )
            await self.db.commit()
        
        return notification
    
    async def send_bulk_notifications(
        self,
        user_ids: List[UUID],
        organization_id: UUID,
        notification_type: NotificationType,
        category: NotificationCategory,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        **kwargs
    ) -> tuple[List[UUID], List[UUID]]:
        """
        Send notification to multiple users.
        
        Returns:
            Tuple of (sent_notification_ids, failed_user_ids)
        """
        sent_ids = []
        failed_ids = []
        
        for user_id in user_ids:
            try:
                notification = await self.send_notification(
                    user_id=user_id,
                    organization_id=organization_id,
                    notification_type=notification_type,
                    category=category,
                    title=title,
                    body=body,
                    priority=priority,
                    **kwargs
                )
                sent_ids.append(notification.id)
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
                failed_ids.append(user_id)
        
        return sent_ids, failed_ids
    
    async def get_user_notifications(
        self,
        user_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
        category: Optional[NotificationCategory] = None,
        unread_only: bool = False,
    ) -> tuple[List[Notification], int, int]:
        """
        Get user's notifications with pagination.
        
        Returns:
            Tuple of (notifications, total_count, unread_count)
        """
        notifications, total = await self.repo.get_user_notifications(
            user_id=user_id,
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            category=category,
            unread_only=unread_only,
        )
        
        unread_count = await self.repo.get_unread_count(user_id, organization_id)
        
        return notifications, total, unread_count
    
    async def mark_as_read(
        self, 
        notification_ids: List[UUID], 
        user_id: UUID
    ) -> int:
        """Mark notifications as read"""
        count = await self.repo.mark_as_read(notification_ids, user_id)
        await self.db.commit()
        return count
    
    async def mark_all_as_read(self, user_id: UUID, organization_id: UUID) -> int:
        """Mark all user's notifications as read"""
        count = await self.repo.mark_all_as_read(user_id, organization_id)
        await self.db.commit()
        return count
    
    async def delete_notification(self, notification_id: UUID, user_id: UUID) -> bool:
        """Delete a notification"""
        deleted = await self.repo.delete_notification(notification_id, user_id)
        if deleted:
            await self.db.commit()
        return deleted
    
    async def get_stats(self, user_id: UUID, organization_id: UUID) -> Dict:
        """Get notification statistics"""
        return await self.repo.get_stats(user_id, organization_id)
    
    async def register_device_token(
        self,
        user_id: UUID,
        device_type: str,
        fcm_token: Optional[str] = None,
        apns_token: Optional[str] = None,
        web_push_subscription: Optional[Dict] = None,
        device_name: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> DeviceToken:
        """Register device token for push notifications"""
        device_token = DeviceToken(
            id=uuid4(),
            user_id=user_id,
            device_type=device_type,
            device_name=device_name,
            device_id=device_id,
            fcm_token=fcm_token,
            apns_token=apns_token,
            web_push_subscription=web_push_subscription,
            is_active=True,
            last_used_at=datetime.utcnow(),
        )
        
        result = await self.repo.create_device_token(device_token)
        await self.db.commit()
        return result
    
    async def get_user_device_tokens(self, user_id: UUID) -> List[DeviceToken]:
        """Get all active device tokens for a user"""
        return await self.repo.get_user_device_tokens(user_id, active_only=True)
    
    async def deactivate_device_token(self, token_id: UUID, user_id: UUID) -> bool:
        """Deactivate a device token"""
        deactivated = await self.repo.deactivate_device_token(token_id, user_id)
        if deactivated:
            await self.db.commit()
        return deactivated
    
    async def update_preferences(
        self,
        user_id: UUID,
        organization_id: UUID,
        category: NotificationCategory,
        push_enabled: bool = True,
        in_app_enabled: bool = True,
        email_enabled: bool = True,
        sms_enabled: bool = False,
        websocket_enabled: bool = True,
        quiet_hours_enabled: bool = False,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None,
    ) -> NotificationPreference:
        """Update notification preferences for a category"""
        preference = NotificationPreference(
            id=uuid4(),
            user_id=user_id,
            organization_id=organization_id,
            category=category,
            push_enabled=push_enabled,
            in_app_enabled=in_app_enabled,
            email_enabled=email_enabled,
            sms_enabled=sms_enabled,
            websocket_enabled=websocket_enabled,
            quiet_hours_enabled=quiet_hours_enabled,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
        )
        
        result = await self.repo.upsert_preference(preference)
        await self.db.commit()
        return result
    
    async def get_preferences(
        self, 
        user_id: UUID, 
        organization_id: UUID
    ) -> List[NotificationPreference]:
        """Get all notification preferences for a user"""
        return await self.repo.get_user_preferences(user_id, organization_id)
    
    # ============== PRIVATE METHODS ==============
    
    def _should_send_notification(
        self,
        notification_type: NotificationType,
        preferences: NotificationPreference,
        priority: NotificationPriority
    ) -> bool:
        """Check if notification should be sent based on preferences"""
        # Check channel-specific preference
        if notification_type == NotificationType.PUSH and not preferences.push_enabled:
            return False
        elif notification_type == NotificationType.IN_APP and not preferences.in_app_enabled:
            return False
        elif notification_type == NotificationType.EMAIL and not preferences.email_enabled:
            return False
        elif notification_type == NotificationType.SMS and not preferences.sms_enabled:
            return False
        elif notification_type == NotificationType.WEBSOCKET and not preferences.websocket_enabled:
            return False
        
        # Check quiet hours (unless urgent)
        if preferences.quiet_hours_enabled and priority != NotificationPriority.URGENT:
            # TODO: Implement quiet hours check
            pass
        
        return True
    
    async def _create_notification_record(
        self,
        user_id: UUID,
        organization_id: UUID,
        notification_type: NotificationType,
        category: NotificationCategory,
        title: str,
        body: str,
        priority: NotificationPriority,
        image_url: Optional[str] = None,
        icon: Optional[str] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        status: NotificationStatus = NotificationStatus.PENDING,
    ) -> Notification:
        """Create notification database record"""
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            organization_id=organization_id,
            type=notification_type,
            category=category,
            priority=priority,
            status=status,
            title=title,
            body=body,
            image_url=image_url,
            icon=icon,
            action_url=action_url,
            action_label=action_label,
            action_data=action_data,
            metadata=metadata,
            expires_at=expires_at,
        )
        
        return await self.repo.create(notification)
    
    async def _send_push_notification(self, notification: Notification) -> None:
        """
        Send push notification via FCM/APNS.
        
        TODO: Implement actual FCM/APNS integration
        """
        # Get user's device tokens
        tokens = await self.repo.get_user_device_tokens(
            user_id=notification.user_id,
            active_only=True
        )
        
        if not tokens:
            logger.warning(f"No active device tokens for user {notification.user_id}")
            await self.repo.update_status(
                notification_id=notification.id,
                status=NotificationStatus.FAILED,
                failed_at=datetime.utcnow(),
                failure_reason="No active device tokens"
            )
            return
        
        # TODO: Send to FCM/APNS
        # For now, just mark as sent
        logger.info(f"Would send push notification to {len(tokens)} device(s)")
        
        await self.repo.update_status(
            notification_id=notification.id,
            status=NotificationStatus.SENT,
            sent_at=datetime.utcnow()
        )
    
    async def _send_email_notification(self, notification: Notification) -> None:
        """
        Send email notification.
        
        TODO: Implement email integration
        """
        logger.info(f"Would send email notification: {notification.title}")
        
        await self.repo.update_status(
            notification_id=notification.id,
            status=NotificationStatus.SENT,
            sent_at=datetime.utcnow()
        )
    
    async def _send_sms_notification(self, notification: Notification) -> None:
        """
        Send SMS notification.
        
        TODO: Implement SMS integration (Twilio, AWS SNS, etc.)
        """
        logger.info(f"Would send SMS notification: {notification.title}")
        
        await self.repo.update_status(
            notification_id=notification.id,
            status=NotificationStatus.SENT,
            sent_at=datetime.utcnow()
        )
    
    async def _send_websocket_notification(self, notification: Notification) -> None:
        """
        Send WebSocket notification.
        
        TODO: Implement WebSocket broadcast
        """
        logger.info(f"Would send WebSocket notification: {notification.title}")
        
        await self.repo.update_status(
            notification_id=notification.id,
            status=NotificationStatus.SENT,
            sent_at=datetime.utcnow()
        )


def get_notification_service(db: AsyncSession) -> NotificationService:
    """Dependency for notification service"""
    return NotificationService(db)
