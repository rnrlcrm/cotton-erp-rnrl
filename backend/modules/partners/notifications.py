"""
Partner Notification Service

Handles automated notifications for:
- KYC renewal reminders (90/60/30/7 days before expiry)
- Amendment request notifications to back office
- Partner status changes
- Approval/rejection notifications

Uses existing event system - event handlers trigger notifications
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.email.service import EmailService
from backend.adapters.sms.service import SMSService
from backend.core.events.emitter import EventEmitter
from backend.modules.partners.events import (
    KYCExpiringEvent,
    AmendmentRequestedEvent,
    PartnerApprovedEvent,
    PartnerRejectedEvent,
    PartnerSuspendedEvent,
)
from backend.modules.partners.models import BusinessPartner
from backend.modules.partners.repositories import BusinessPartnerRepository


class PartnerNotificationService:
    """Handle all partner-related notifications"""
    
    def __init__(
        self,
        db: AsyncSession,
        email_service: EmailService,
        sms_service: SMSService
    ):
        self.db = db
        self.email_service = email_service
        self.sms_service = sms_service
    
    async def send_kyc_reminder(
        self,
        partner: BusinessPartner,
        days_remaining: int
    ) -> None:
        """Send KYC renewal reminder"""
        
        # Determine urgency
        if days_remaining <= 7:
            urgency = "CRITICAL"
            subject = f"⚠️ URGENT: KYC expires in {days_remaining} days"
        elif days_remaining <= 30:
            urgency = "HIGH"
            subject = f"⚠️ Important: KYC expires in {days_remaining} days"
        else:
            urgency = "NORMAL"
            subject = f"Reminder: KYC expires in {days_remaining} days"
        
        # Email content
        email_body = f"""
Dear {partner.primary_contact_person},

This is a reminder that your KYC verification for {partner.legal_business_name} 
will expire in {days_remaining} days.

KYC Expiry Date: {partner.kyc_expiry_date.strftime('%d %B %Y')}

Please initiate the KYC renewal process to avoid service disruption.

To renew:
1. Log in to your account
2. Go to Partner Profile
3. Click "Renew KYC"
4. Upload fresh documents

If you have any questions, please contact our support team.

Regards,
Cotton ERP Team
"""
        
        # Send email
        await self.email_service.send(
            to=partner.primary_contact_email,
            subject=subject,
            body=email_body,
            priority=urgency
        )
        
        # Send SMS for critical urgency
        if urgency == "CRITICAL":
            sms_body = f"URGENT: Your KYC expires in {days_remaining} days. Renew now to avoid suspension. - Cotton ERP"
            await self.sms_service.send(
                to=partner.primary_contact_phone,
                body=sms_body
            )
    
    async def send_amendment_notification_to_backoffice(
        self,
        partner: BusinessPartner,
        amendment_type: str,
        field_name: str,
        old_value: str,
        new_value: str,
        reason: str
    ) -> None:
        """Notify back office about amendment request"""
        
        # Determine approver based on amendment type
        if amendment_type in ["bank_change", "address_change"]:
            approver_email = "director@cottonerp.com"  # High-risk changes
        else:
            approver_email = "manager@cottonerp.com"
        
        subject = f"Amendment Request: {partner.legal_business_name}"
        
        email_body = f"""
New Amendment Request Received

Partner: {partner.legal_business_name} ({partner.tax_id_number})
Amendment Type: {amendment_type}

Field: {field_name}
Current Value: {old_value}
Requested Value: {new_value}

Reason: {reason}

Risk Category: {partner.risk_category or 'N/A'}

Action Required: Review and approve/reject this amendment.

[Approve] [Reject] [View Details]

This is an automated notification.
"""
        
        await self.email_service.send(
            to=approver_email,
            subject=subject,
            body=email_body,
            priority="HIGH"
        )
    
    async def send_approval_notification(
        self,
        partner: BusinessPartner,
        approval_notes: str | None
    ) -> None:
        """Notify partner about approval"""
        
        subject = f"✅ Partner Application Approved - {partner.legal_business_name}"
        
        email_body = f"""
Dear {partner.primary_contact_person},

Congratulations! Your partner application has been approved.

Partner Details:
- Business Name: {partner.legal_business_name}
- GSTIN: {partner.tax_id_number}
- Partner Type: {partner.partner_type}
- KYC Valid Until: {partner.kyc_expiry_date.strftime('%d %B %Y')}

You can now:
✓ Access all platform features
✓ Start transactions
✓ Invite employees (max 2)

{f'Approval Notes: {approval_notes}' if approval_notes else ''}

Welcome to Cotton ERP!

Best regards,
Cotton ERP Team
"""
        
        await self.email_service.send(
            to=partner.primary_contact_email,
            subject=subject,
            body=email_body
        )
    
    async def send_rejection_notification(
        self,
        partner_email: str,
        partner_name: str,
        business_name: str,
        rejection_reason: str
    ) -> None:
        """Notify partner about rejection"""
        
        subject = f"Partner Application Update - {business_name}"
        
        email_body = f"""
Dear {partner_name},

Thank you for your interest in partnering with Cotton ERP.

After careful review, we regret to inform you that we are unable to approve 
your partner application at this time.

Reason: {rejection_reason}

You may reapply after addressing the concerns mentioned above.

If you have any questions, please contact our support team.

Regards,
Cotton ERP Team
"""
        
        await self.email_service.send(
            to=partner_email,
            subject=subject,
            body=email_body
        )
    
    async def send_suspension_notification(
        self,
        partner: BusinessPartner,
        reason: str
    ) -> None:
        """Notify partner about suspension"""
        
        subject = f"⚠️ Account Suspended - {partner.legal_business_name}"
        
        email_body = f"""
Dear {partner.primary_contact_person},

Your partner account has been suspended.

Reason: {reason}

Impact:
- No new transactions can be initiated
- Existing transactions will be completed
- Access to certain features is restricted

To reactivate your account:
1. Address the suspension reason
2. Contact our support team
3. Complete any pending compliance requirements

For assistance, please contact support@cottonerp.com

Regards,
Cotton ERP Team
"""
        
        await self.email_service.send(
            to=partner.primary_contact_email,
            subject=subject,
            body=email_body,
            priority="HIGH"
        )
        
        # Send SMS
        await self.sms_service.send(
            to=partner.primary_contact_phone,
            body=f"Your Cotton ERP account has been suspended. Reason: {reason}. Contact support immediately."
        )


async def check_and_send_kyc_reminders(
    db: AsyncSession,
    email_service: EmailService,
    sms_service: SMSService
) -> int:
    """
    Check for expiring KYC and send reminders
    
    This function should be called by a scheduled job (Celery/APScheduler)
    to run daily at 9 AM
    
    Returns: Number of reminders sent
    """
    notification_service = PartnerNotificationService(db, email_service, sms_service)
    
    now = datetime.utcnow()
    reminder_thresholds = [90, 60, 30, 7]  # Days before expiry
    
    reminders_sent = 0
    
    for days in reminder_thresholds:
        target_date = now + timedelta(days=days)
        
        # Find partners expiring on this date
        query = select(BusinessPartner).where(
            BusinessPartner.is_deleted == False,
            BusinessPartner.status == "active",
            BusinessPartner.kyc_expiry_date.isnot(None),
            # Check if expiry is within the next 'days' days
            BusinessPartner.kyc_expiry_date <= target_date,
            BusinessPartner.kyc_expiry_date > now
        )
        
        result = await db.execute(query)
        partners = result.scalars().all()
        
        for partner in partners:
            days_remaining = (partner.kyc_expiry_date - now).days
            
            # Only send reminder if exactly at threshold
            if days_remaining in reminder_thresholds:
                await notification_service.send_kyc_reminder(partner, days_remaining)
                reminders_sent += 1
    
    return reminders_sent
