"""
Notification Repository

Database operations for notifications.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.notifications.models import (
    DeviceToken,
    Notification,
    NotificationCategory,
    NotificationPreference,
    NotificationStatus,
)


class NotificationRepository:
    """Repository for notification database operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============== NOTIFICATION CRUD ==============
    
    async def create(self, notification: Notification) -> Notification:
        """Create a new notification"""
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification
    
    async def get_by_id(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        """Get notification by ID (with user ownership check)"""
        query = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_notifications(
        self,
        user_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
        category: Optional[NotificationCategory] = None,
        unread_only: bool = False,
    ) -> tuple[List[Notification], int]:
        """
        Get user's notifications with pagination.
        
        Returns:
            Tuple of (notifications, total_count)
        """
        # Build query
        query = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id
            )
        )
        
        # Apply filters
        if category:
            query = query.where(Notification.category == category)
        
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Paginate and order
        query = query.order_by(desc(Notification.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        return list(notifications), total
    
    async def get_unread_count(self, user_id: UUID, organization_id: UUID) -> int:
        """Get count of unread notifications"""
        query = select(func.count()).where(
            and_(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.read_at.is_(None)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one()
    
    async def mark_as_read(
        self, 
        notification_ids: List[UUID], 
        user_id: UUID
    ) -> int:
        """
        Mark notifications as read.
        
        Returns:
            Number of notifications marked as read
        """
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.id.in_(notification_ids),
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None)
                )
            )
            .values(read_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        return result.rowcount
    
    async def mark_all_as_read(self, user_id: UUID, organization_id: UUID) -> int:
        """
        Mark all user's notifications as read.
        
        Returns:
            Number of notifications marked as read
        """
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.organization_id == organization_id,
                    Notification.read_at.is_(None)
                )
            )
            .values(read_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        return result.rowcount
    
    async def delete_notification(self, notification_id: UUID, user_id: UUID) -> bool:
        """
        Delete a notification.
        
        Returns:
            True if deleted, False if not found
        """
        stmt = delete(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    async def update_status(
        self,
        notification_id: UUID,
        status: NotificationStatus,
        **extra_fields
    ) -> None:
        """Update notification status and optional fields"""
        values = {"status": status, "updated_at": datetime.utcnow()}
        values.update(extra_fields)
        
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(**values)
        )
        await self.db.execute(stmt)
    
    async def get_stats(self, user_id: UUID, organization_id: UUID) -> Dict:
        """Get notification statistics for user"""
        # Total count
        total_query = select(func.count()).where(
            and_(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id
            )
        )
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar_one()
        
        # Unread count
        unread_count = await self.get_unread_count(user_id, organization_id)
        
        # By category
        category_query = (
            select(
                Notification.category,
                func.count()
            )
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.organization_id == organization_id
                )
            )
            .group_by(Notification.category)
        )
        category_result = await self.db.execute(category_query)
        by_category = {cat.value: count for cat, count in category_result.all()}
        
        # By priority
        priority_query = (
            select(
                Notification.priority,
                func.count()
            )
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.organization_id == organization_id
                )
            )
            .group_by(Notification.priority)
        )
        priority_result = await self.db.execute(priority_query)
        by_priority = {pri.value: count for pri, count in priority_result.all()}
        
        return {
            "total_count": total_count,
            "unread_count": unread_count,
            "read_count": total_count - unread_count,
            "by_category": by_category,
            "by_priority": by_priority,
        }
    
    # ============== DEVICE TOKEN CRUD ==============
    
    async def create_device_token(self, device_token: DeviceToken) -> DeviceToken:
        """Create or update device token"""
        # Check if token already exists
        if device_token.fcm_token:
            existing_query = select(DeviceToken).where(
                DeviceToken.fcm_token == device_token.fcm_token
            )
            existing_result = await self.db.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.device_name = device_token.device_name
                existing.device_id = device_token.device_id
                existing.is_active = True
                existing.last_used_at = datetime.utcnow()
                await self.db.flush()
                return existing
        
        # Create new
        self.db.add(device_token)
        await self.db.flush()
        await self.db.refresh(device_token)
        return device_token
    
    async def get_user_device_tokens(
        self, 
        user_id: UUID, 
        active_only: bool = True
    ) -> List[DeviceToken]:
        """Get all device tokens for a user"""
        query = select(DeviceToken).where(DeviceToken.user_id == user_id)
        
        if active_only:
            query = query.where(DeviceToken.is_active == True)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def deactivate_device_token(self, token_id: UUID, user_id: UUID) -> bool:
        """Deactivate a device token"""
        stmt = (
            update(DeviceToken)
            .where(
                and_(
                    DeviceToken.id == token_id,
                    DeviceToken.user_id == user_id
                )
            )
            .values(is_active=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
    
    # ============== PREFERENCES CRUD ==============
    
    async def get_user_preferences(
        self, 
        user_id: UUID, 
        organization_id: UUID
    ) -> List[NotificationPreference]:
        """Get all notification preferences for a user"""
        query = select(NotificationPreference).where(
            and_(
                NotificationPreference.user_id == user_id,
                NotificationPreference.organization_id == organization_id
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_preference(
        self,
        user_id: UUID,
        organization_id: UUID,
        category: NotificationCategory
    ) -> Optional[NotificationPreference]:
        """Get preference for specific category"""
        query = select(NotificationPreference).where(
            and_(
                NotificationPreference.user_id == user_id,
                NotificationPreference.organization_id == organization_id,
                NotificationPreference.category == category
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def upsert_preference(
        self, 
        preference: NotificationPreference
    ) -> NotificationPreference:
        """Create or update notification preference"""
        # Check if exists
        existing = await self.get_preference(
            preference.user_id,
            preference.organization_id,
            preference.category
        )
        
        if existing:
            # Update existing
            for key, value in preference.__dict__.items():
                if not key.startswith('_') and key not in ['id', 'created_at']:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            await self.db.flush()
            return existing
        else:
            # Create new
            self.db.add(preference)
            await self.db.flush()
            await self.db.refresh(preference)
            return preference
