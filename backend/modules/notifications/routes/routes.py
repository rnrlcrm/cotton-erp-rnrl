"""
Notification API Routes

REST API endpoints for notification management.

Features:
- Send notifications (single/bulk)
- Get user notifications (paginated)
- Mark as read
- Delete notifications
- Manage device tokens
- Update notification preferences
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.capabilities import Capabilities, RequireCapability
from backend.core.auth.deps import get_current_user
from backend.db.session import get_db
from backend.modules.notifications.models import NotificationCategory
from backend.modules.notifications.schemas import (
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
from backend.modules.notifications.services import get_notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============== NOTIFICATION ENDPOINTS ==============

@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Notification",
    description="Send a notification to a specific user"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_USERS)  # Only admins can send notifications
async def send_notification(
    request: SendNotificationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a notification to a user.
    
    Requires: ADMIN_MANAGE_USERS capability
    
    The notification will be delivered via the specified channel
    based on user preferences.
    """
    service = get_notification_service(db)
    
    notification = await service.send_notification(
        user_id=request.user_id,
        organization_id=current_user["organization_id"],
        notification_type=request.type,
        category=request.category,
        title=request.title,
        body=request.body,
        priority=request.priority,
        image_url=request.image_url,
        icon=request.icon,
        action_url=request.action_url,
        action_label=request.action_label,
        action_data=request.action_data,
        metadata=request.metadata,
        expires_at=request.expires_at,
    )
    
    return NotificationResponse.model_validate(notification)


@router.post(
    "/bulk",
    response_model=BulkSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Bulk Notifications",
    description="Send the same notification to multiple users"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_USERS)
async def send_bulk_notifications(
    request: BulkSendNotificationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send notification to multiple users at once.
    
    Requires: ADMIN_MANAGE_USERS capability
    
    Useful for:
    - System announcements
    - Marketing campaigns
    - Critical alerts to all users
    """
    service = get_notification_service(db)
    
    sent_ids, failed_user_ids = await service.send_bulk_notifications(
        user_ids=request.user_ids,
        organization_id=current_user["organization_id"],
        notification_type=request.type,
        category=request.category,
        title=request.title,
        body=request.body,
        priority=request.priority,
        image_url=request.image_url,
        icon=request.icon,
        action_url=request.action_url,
        action_label=request.action_label,
        action_data=request.action_data,
        metadata=request.metadata,
        expires_at=request.expires_at,
    )
    
    return BulkSendResponse(
        total_sent=len(sent_ids),
        notification_ids=sent_ids,
        failed_user_ids=failed_user_ids,
    )


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Get My Notifications",
    description="Get all notifications for current user with pagination"
)
async def get_my_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    category: Optional[NotificationCategory] = Query(None, description="Filter by category"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get your notifications.
    
    Mobile/Web apps use this to:
    - Display notification list
    - Show unread badge count
    - Filter by category
    """
    service = get_notification_service(db)
    
    notifications, total, unread_count = await service.get_user_notifications(
        user_id=current_user["user_id"],
        organization_id=current_user["organization_id"],
        page=page,
        page_size=page_size,
        category=category,
        unread_only=unread_only,
    )
    
    return NotificationListResponse(
        total=total,
        unread_count=unread_count,
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get(
    "/stats",
    response_model=NotificationStatsResponse,
    summary="Get Notification Statistics",
    description="Get statistics about user's notifications"
)
async def get_notification_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notification statistics.
    
    Shows:
    - Total count
    - Unread count
    - Count by category
    - Count by priority
    """
    service = get_notification_service(db)
    
    stats = await service.get_stats(
        user_id=current_user["user_id"],
        organization_id=current_user["organization_id"],
    )
    
    return NotificationStatsResponse(**stats)


@router.post(
    "/mark-read",
    response_model=MarkAsReadResponse,
    summary="Mark Notifications as Read",
    description="Mark one or more notifications as read"
)
async def mark_as_read(
    request: MarkAsReadRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark notifications as read.
    
    Use when:
    - User opens notification
    - User views notification list
    - Bulk marking as read
    """
    service = get_notification_service(db)
    
    count = await service.mark_as_read(
        notification_ids=request.notification_ids,
        user_id=current_user["user_id"],
    )
    
    return MarkAsReadResponse(
        marked_count=count,
        notification_ids=request.notification_ids[:count],
    )


@router.post(
    "/mark-all-read",
    response_model=MarkAsReadResponse,
    summary="Mark All as Read",
    description="Mark all user's notifications as read"
)
async def mark_all_as_read(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all notifications as read.
    
    Useful for "Mark all as read" button in UI.
    """
    service = get_notification_service(db)
    
    count = await service.mark_all_as_read(
        user_id=current_user["user_id"],
        organization_id=current_user["organization_id"],
    )
    
    return MarkAsReadResponse(
        marked_count=count,
        notification_ids=[],
    )


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Notification",
    description="Delete a specific notification"
)
async def delete_notification(
    notification_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a notification.
    
    Use for:
    - User dismissing notification
    - Removing old notifications
    """
    service = get_notification_service(db)
    
    deleted = await service.delete_notification(
        notification_id=notification_id,
        user_id=current_user["user_id"],
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )


# ============== DEVICE TOKEN ENDPOINTS ==============

@router.post(
    "/devices",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Device Token",
    description="Register device token for push notifications"
)
async def register_device_token(
    request: RegisterDeviceTokenRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register device token for push notifications.
    
    Mobile apps call this on:
    - App launch
    - Token refresh
    - User login
    
    Supports:
    - FCM (Firebase Cloud Messaging) for Android
    - APNS (Apple Push Notification Service) for iOS
    - Web Push for web browsers
    """
    service = get_notification_service(db)
    
    device_token = await service.register_device_token(
        user_id=current_user["user_id"],
        device_type=request.device_type,
        fcm_token=request.fcm_token,
        apns_token=request.apns_token,
        web_push_subscription=request.web_push_subscription,
        device_name=request.device_name,
        device_id=request.device_id,
    )
    
    return DeviceTokenResponse.model_validate(device_token)


@router.get(
    "/devices",
    response_model=List[DeviceTokenResponse],
    summary="Get My Device Tokens",
    description="Get all registered devices for current user"
)
async def get_my_devices(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all registered devices.
    
    Shows:
    - Device type (iOS, Android, Web)
    - Device name
    - Last used time
    - Active status
    """
    service = get_notification_service(db)
    
    devices = await service.get_user_device_tokens(
        user_id=current_user["user_id"]
    )
    
    return [DeviceTokenResponse.model_validate(d) for d in devices]


@router.delete(
    "/devices/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate Device Token",
    description="Deactivate a device token (stop push notifications)"
)
async def deactivate_device_token(
    token_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate device token.
    
    Use when:
    - User logs out
    - Device is lost/stolen
    - User wants to stop notifications on specific device
    """
    service = get_notification_service(db)
    
    deactivated = await service.deactivate_device_token(
        token_id=token_id,
        user_id=current_user["user_id"],
    )
    
    if not deactivated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found"
        )


# ============== PREFERENCE ENDPOINTS ==============

@router.get(
    "/preferences",
    response_model=List[NotificationPreferenceResponse],
    summary="Get Notification Preferences",
    description="Get all notification preferences for current user"
)
async def get_preferences(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notification preferences.
    
    Shows which types of notifications user wants to receive
    per category (Trade, Partner, Payment, etc.)
    """
    service = get_notification_service(db)
    
    preferences = await service.get_preferences(
        user_id=current_user["user_id"],
        organization_id=current_user["organization_id"],
    )
    
    return [NotificationPreferenceResponse.model_validate(p) for p in preferences]


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update Notification Preferences",
    description="Update notification preferences for a category"
)
async def update_preferences(
    request: UpdateNotificationPreferencesRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update notification preferences.
    
    User can control:
    - Which channels to receive notifications (push, email, SMS)
    - Quiet hours (do not disturb)
    - Preferences per category
    """
    service = get_notification_service(db)
    
    preference = await service.update_preferences(
        user_id=current_user["user_id"],
        organization_id=current_user["organization_id"],
        category=request.category,
        push_enabled=request.push_enabled,
        in_app_enabled=request.in_app_enabled,
        email_enabled=request.email_enabled,
        sms_enabled=request.sms_enabled,
        websocket_enabled=request.websocket_enabled,
        quiet_hours_enabled=request.quiet_hours_enabled,
        quiet_hours_start=request.quiet_hours_start,
        quiet_hours_end=request.quiet_hours_end,
    )
    
    return NotificationPreferenceResponse.model_validate(preference)
