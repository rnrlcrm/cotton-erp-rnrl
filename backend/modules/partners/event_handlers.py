"""
Partner Event Handlers

Event handlers that trigger notifications and other side effects
when partner-related events are emitted.

Handlers are registered with the event emitter and execute asynchronously.
"""

from __future__ import annotations

from backend.adapters.email.service import EmailService
from backend.adapters.sms.service import SMSService
from backend.core.events.emitter import EventEmitter
from backend.modules.partners.events import (
    AmendmentApprovedEvent,
    AmendmentRejectedEvent,
    AmendmentRequestedEvent,
    KYCExpiringEvent,
    PartnerApprovedEvent,
    PartnerRejectedEvent,
    PartnerSuspendedEvent,
)
from backend.modules.partners.notifications import PartnerNotificationService
from backend.modules.partners.repositories import BusinessPartnerRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def register_partner_event_handlers(
    emitter: EventEmitter,
    db: AsyncSession,
    email_service: EmailService,
    sms_service: SMSService
) -> None:
    """Register all partner event handlers"""
    
    notification_service = PartnerNotificationService(db, email_service, sms_service)
    partner_repo = BusinessPartnerRepository(db)
    
    # KYC Expiring Handler
    @emitter.on(KYCExpiringEvent)
    async def on_kyc_expiring(event: KYCExpiringEvent):
        """Send KYC renewal reminder when KYC is expiring"""
        partner = await partner_repo.get_by_id(event.partner_id, event.organization_id)
        if partner:
            await notification_service.send_kyc_reminder(
                partner=partner,
                days_remaining=event.days_remaining
            )
    
    # Partner Approved Handler
    @emitter.on(PartnerApprovedEvent)
    async def on_partner_approved(event: PartnerApprovedEvent):
        """Send approval notification to partner"""
        partner = await partner_repo.get_by_id(event.partner_id, event.organization_id)
        if partner:
            await notification_service.send_approval_notification(
                partner=partner,
                approval_notes=event.approval_notes
            )
    
    # Partner Rejected Handler
    @emitter.on(PartnerRejectedEvent)
    async def on_partner_rejected(event: PartnerRejectedEvent):
        """Send rejection notification to partner"""
        # Note: We don't have partner record yet, so use event data
        await notification_service.send_rejection_notification(
            partner_email=event.contact_email,
            partner_name=event.contact_person,
            business_name=event.business_name,
            rejection_reason=event.rejection_reason
        )
    
    # Partner Suspended Handler
    @emitter.on(PartnerSuspendedEvent)
    async def on_partner_suspended(event: PartnerSuspendedEvent):
        """Send suspension notification to partner"""
        partner = await partner_repo.get_by_id(event.partner_id, event.organization_id)
        if partner:
            await notification_service.send_suspension_notification(
                partner=partner,
                reason=event.reason
            )
    
    # Amendment Requested Handler
    @emitter.on(AmendmentRequestedEvent)
    async def on_amendment_requested(event: AmendmentRequestedEvent):
        """Notify back office when amendment is requested"""
        partner = await partner_repo.get_by_id(event.partner_id, event.organization_id)
        if partner:
            await notification_service.send_amendment_notification_to_backoffice(
                partner=partner,
                amendment_type=event.amendment_type,
                field_name=event.field_name,
                old_value=event.old_value or '',
                new_value=event.new_value,
                reason=event.reason
            )
    
    # Amendment Approved Handler
    @emitter.on(AmendmentApprovedEvent)
    async def on_amendment_approved(event: AmendmentApprovedEvent):
        """Notify partner when amendment is approved"""
        partner = await partner_repo.get_by_id(event.partner_id, event.organization_id)
        if partner:
            await email_service.send(
                to=partner.primary_contact_email,
                subject=f"Amendment Approved - {partner.legal_business_name}",
                body=f"""
Dear {partner.primary_contact_person},

Your amendment request has been approved.

Field Updated: {event.field_name}
New Value: {event.new_value}

The changes are now effective.

Regards,
Commodity ERP Team
"""
            )
    
    # Amendment Rejected Handler
    @emitter.on(AmendmentRejectedEvent)
    async def on_amendment_rejected(event: AmendmentRejectedEvent):
        """Notify partner when amendment is rejected"""
        partner = await partner_repo.get_by_id(event.partner_id, event.organization_id)
        if partner:
            await email_service.send(
                to=partner.primary_contact_email,
                subject=f"Amendment Request Declined - {partner.legal_business_name}",
                body=f"""
Dear {partner.primary_contact_person},

Your amendment request has been declined.

Field: {event.field_name}
Reason: {event.rejection_reason}

Please contact support if you have questions.

Regards,
Commodity ERP Team
"""
            )
