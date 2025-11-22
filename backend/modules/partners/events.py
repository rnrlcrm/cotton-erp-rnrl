"""
Partner Module Events

Defines all events that occur during partner lifecycle.

Events:
- OnboardingStarted
- OnboardingSubmitted  
- PartnerApproved
- PartnerRejected
- KYCExpiringEvent (30 days before)
- KYCExpiredEvent
- KYCRenewalInitiated
- KYCRenewalCompleted
- AmendmentRequested
- AmendmentApproved
- AmendmentRejected
- EmployeeInvited
- EmployeeActivated
- EmployeeDeactivated
- RiskScoreChanged
- PartnerSuspended
- PartnerActivated
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from backend.core.events.base import BaseEvent, EventMetadata


class OnboardingStartedEvent(BaseEvent):
    """Emitted when partner starts onboarding"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # application_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_type, business_name, gstin
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.onboarding.started",
            aggregate_id=aggregate_id,
            aggregate_type="partner_application",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class OnboardingSubmittedEvent(BaseEvent):
    """Emitted when application submitted for approval"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # application_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # risk_score, approval_route
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.onboarding.submitted",
            aggregate_id=aggregate_id,
            aggregate_type="partner_application",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class PartnerApprovedEvent(BaseEvent):
    """Emitted when partner is approved"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # partner_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # business_name, partner_type, risk_score, credit_limit
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.approved",
            aggregate_id=aggregate_id,
            aggregate_type="partner",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class PartnerRejectedEvent(BaseEvent):
    """Emitted when partner application is rejected"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # application_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # business_name, rejection_reason
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.rejected",
            aggregate_id=aggregate_id,
            aggregate_type="partner_application",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class KYCExpiringEvent(BaseEvent):
    """Emitted when KYC is expiring soon (30 days before)"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # partner_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # business_name, days_to_expiry, expiry_date
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.kyc.expiring",
            aggregate_id=aggregate_id,
            aggregate_type="partner",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class KYCExpiredEvent(BaseEvent):
    """Emitted when KYC has expired"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # partner_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # business_name, expiry_date
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.kyc.expired",
            aggregate_id=aggregate_id,
            aggregate_type="partner",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class KYCRenewalInitiatedEvent(BaseEvent):
    """Emitted when KYC renewal is initiated"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # renewal_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, business_name, due_date
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.kyc.renewal.initiated",
            aggregate_id=aggregate_id,
            aggregate_type="kyc_renewal",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class KYCRenewalCompletedEvent(BaseEvent):
    """Emitted when KYC renewal is completed"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # renewal_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, business_name, new_expiry_date, verification_passed
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.kyc.renewal.completed",
            aggregate_id=aggregate_id,
            aggregate_type="kyc_renewal",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class AmendmentRequestedEvent(BaseEvent):
    """Emitted when partner requests amendment"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # amendment_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, amendment_type, field_name, old_value, new_value
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.amendment.requested",
            aggregate_id=aggregate_id,
            aggregate_type="amendment",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class AmendmentApprovedEvent(BaseEvent):
    """Emitted when amendment is approved"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # amendment_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, amendment_type, changes_applied
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.amendment.approved",
            aggregate_id=aggregate_id,
            aggregate_type="amendment",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class AmendmentRejectedEvent(BaseEvent):
    """Emitted when amendment is rejected"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # amendment_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, amendment_type, rejection_reason
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.amendment.rejected",
            aggregate_id=aggregate_id,
            aggregate_type="amendment",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class EmployeeInvitedEvent(BaseEvent):
    """Emitted when partner invites an employee"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # employee_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, employee_name, employee_email
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.employee.invited",
            aggregate_id=aggregate_id,
            aggregate_type="partner_employee",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class EmployeeActivatedEvent(BaseEvent):
    """Emitted when employee accepts invitation and activates"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # employee_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, employee_name
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.employee.activated",
            aggregate_id=aggregate_id,
            aggregate_type="partner_employee",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class EmployeeDeactivatedEvent(BaseEvent):
    """Emitted when employee is deactivated"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # employee_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, employee_name, reason
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.employee.deactivated",
            aggregate_id=aggregate_id,
            aggregate_type="partner_employee",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class RiskScoreChangedEvent(BaseEvent):
    """Emitted when partner risk score changes significantly"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # partner_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # old_score, new_score, old_category, new_category, reason
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.risk.score.changed",
            aggregate_id=aggregate_id,
            aggregate_type="partner",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class PartnerSuspendedEvent(BaseEvent):
    """Emitted when partner is suspended"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # partner_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # business_name, reason
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.suspended",
            aggregate_id=aggregate_id,
            aggregate_type="partner",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class PartnerActivatedEvent(BaseEvent):
    """Emitted when suspended partner is re-activated"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # partner_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # business_name
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.activated",
            aggregate_id=aggregate_id,
            aggregate_type="partner",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class DocumentUploadedEvent(BaseEvent):
    """Emitted when partner uploads a document"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # document_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, document_type, file_name
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.document.uploaded",
            aggregate_id=aggregate_id,
            aggregate_type="partner_document",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class DocumentVerifiedEvent(BaseEvent):
    """Emitted when document is verified (OCR extraction successful)"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # document_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, document_type, extracted_data, confidence
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.document.verified",
            aggregate_id=aggregate_id,
            aggregate_type="partner_document",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class VehicleAddedEvent(BaseEvent):
    """Emitted when transporter adds a vehicle"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # vehicle_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, registration_number, vehicle_type
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.vehicle.added",
            aggregate_id=aggregate_id,
            aggregate_type="partner_vehicle",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class VehicleVerifiedEvent(BaseEvent):
    """Emitted when vehicle RC is verified from RTO"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # vehicle_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # partner_id, registration_number, verification_details
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.vehicle.verified",
            aggregate_id=aggregate_id,
            aggregate_type="partner_vehicle",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class PartnerLocationAddedEvent(BaseEvent):
    """Emitted when partner adds a new location (ship-to, warehouse, branch, etc.)"""
    
    def __init__(
        self,
        partner_id: uuid.UUID,
        location_id: uuid.UUID,
        location_type: str,
        location_name: str,
        added_by: uuid.UUID,
        google_maps_tagged: bool = False,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="partner.location.added",
            aggregate_id=location_id,
            aggregate_type="partner_location",
            user_id=added_by,
            data={
                "partner_id": str(partner_id),
                "location_type": location_type,
                "location_name": location_name,
                "google_maps_tagged": google_maps_tagged,
                "latitude": latitude,
                "longitude": longitude,
            },
            metadata=metadata,
        )

