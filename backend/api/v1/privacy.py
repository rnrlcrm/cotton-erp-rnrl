"""
Privacy and GDPR API Endpoints

Implements user-facing GDPR rights:
- Article 7: Consent management
- Article 15: Right of access (data export)
- Article 17: Right to erasure (account deletion)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.core.auth.dependencies import get_current_user
from backend.core.gdpr.consent import ConsentType, PrivacyService, UserConsent
from backend.core.gdpr.user_rights import DataExportService, DeletionService, UserRightType
from backend.domain.users.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/privacy", tags=["privacy"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ConsentRequest(BaseModel):
    """Request to give consent"""
    consent_type: ConsentType
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ConsentWithdrawalRequest(BaseModel):
    """Request to withdraw consent"""
    consent_type: ConsentType


class ConsentResponse(BaseModel):
    """Consent record response"""
    consent_type: ConsentType
    given: bool
    given_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    version: str
    
    class Config:
        from_attributes = True


class ConsentHistoryResponse(BaseModel):
    """Full consent history"""
    consents: Dict[str, List[Dict]]


class DataExportResponse(BaseModel):
    """Data export response"""
    request_id: UUID
    message: str = "Your data export has been requested. You will receive it via email within 30 days as required by GDPR."


class AccountDeletionRequest(BaseModel):
    """Request to delete account"""
    reason: Optional[str] = Field(None, max_length=500)
    confirm: bool = Field(..., description="Must be true to confirm deletion")


class AccountDeletionResponse(BaseModel):
    """Account deletion response"""
    request_id: UUID
    message: str = "Your account deletion request has been submitted. Your account will be deleted within 30 days as required by GDPR."


# ============================================================================
# Consent Management Endpoints
# ============================================================================

@router.post("/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def give_consent(
    request: ConsentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Give consent for data processing (GDPR Article 7).
    
    Consent is:
    - Freely given
    - Specific
    - Informed
    - Unambiguous
    - Withdrawable
    
    Proof of consent is stored (IP, user agent, timestamp).
    """
    privacy_service = PrivacyService(db)
    
    consent = await privacy_service.give_consent(
        user_id=current_user.id,
        consent_type=request.consent_type,
        ip_address=request.ip_address,
        user_agent=request.user_agent,
    )
    
    await db.commit()
    
    # Get version info
    version_info = await privacy_service.get_active_consent_versions()
    version = version_info.get(request.consent_type)
    
    logger.info(f"User {current_user.id} gave consent for {request.consent_type}")
    
    return ConsentResponse(
        consent_type=consent.consent_type,
        given=consent.given,
        given_at=consent.given_at.isoformat() if consent.given_at else None,
        withdrawn_at=consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
        version=version.version if version else "unknown",
    )


@router.delete("/consent/{consent_type}", response_model=ConsentResponse)
async def withdraw_consent(
    consent_type: ConsentType,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Withdraw consent (GDPR Article 7.3).
    
    "It shall be as easy to withdraw as to give consent."
    
    Withdrawing consent does not affect lawfulness of processing
    based on consent before withdrawal.
    """
    privacy_service = PrivacyService(db)
    
    consent = await privacy_service.withdraw_consent(
        user_id=current_user.id,
        consent_type=consent_type,
    )
    
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active consent found for {consent_type}",
        )
    
    await db.commit()
    
    # Get version info
    version_info = await privacy_service.get_active_consent_versions()
    version = version_info.get(consent_type)
    
    logger.info(f"User {current_user.id} withdrew consent for {consent_type}")
    
    return ConsentResponse(
        consent_type=consent.consent_type,
        given=consent.given,
        given_at=consent.given_at.isoformat() if consent.given_at else None,
        withdrawn_at=consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
        version=version.version if version else "unknown",
    )


@router.get("/consent/history", response_model=ConsentHistoryResponse)
async def get_consent_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full consent history (GDPR Article 15 - transparency).
    
    Shows all consents given and withdrawn over time.
    """
    privacy_service = PrivacyService(db)
    
    history = await privacy_service.get_consent_history(current_user.id)
    
    return ConsentHistoryResponse(consents=history)


# ============================================================================
# Data Export Endpoints (Article 15 - Right of Access)
# ============================================================================

@router.post("/export", response_model=DataExportResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_data_export(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request data export (GDPR Article 15 - Right of access).
    
    You have the right to obtain:
    - Copy of your personal data
    - Information about processing
    - Purposes of processing
    - Categories of data
    - Recipients of data
    - Storage periods
    - Your rights
    
    Data will be provided in a structured, commonly used,
    machine-readable format (JSON).
    
    Response time: Within 1 month (can be extended to 3 months
    for complex requests).
    """
    export_service = DataExportService(db)
    
    # Create export request
    request_obj = await export_service.create_export_request(
        user_id=current_user.id,
        metadata={"email": current_user.email},
    )
    
    await db.commit()
    
    # In production, this would trigger an async job to:
    # 1. Export all user data
    # 2. Create secure download link
    # 3. Send email to user
    # 4. Auto-delete download after 7 days
    
    logger.info(f"User {current_user.id} requested data export: {request_obj.id}")
    
    return DataExportResponse(
        request_id=request_obj.id,
        message=f"Your data export has been requested (Request ID: {request_obj.id}). You will receive a secure download link via email within 30 days.",
    )


@router.get("/export/{request_id}")
async def get_data_export(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download data export (for testing - in production use secure link).
    
    This endpoint would typically be protected with a signed token
    and auto-expire after 7 days.
    """
    export_service = DataExportService(db)
    
    # Export data
    export_data = await export_service.export_user_data(current_user.id)
    
    # Complete request
    await export_service.complete_export_request(request_id, export_data)
    await db.commit()
    
    return export_data


# ============================================================================
# Account Deletion Endpoints (Article 17 - Right to Erasure)
# ============================================================================

@router.delete("/account", response_model=AccountDeletionResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_account_deletion(
    request: AccountDeletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request account deletion (GDPR Article 17 - Right to erasure).
    
    You have the right to erasure ("right to be forgotten") when:
    - Data no longer necessary for purposes collected
    - You withdraw consent
    - You object to processing
    - Data processed unlawfully
    - Legal obligation to erase
    
    Exceptions (we may refuse):
    - Legal obligation to retain data (e.g., accounting, tax)
    - Legal claims (disputes, litigation)
    - Public interest
    
    What happens:
    1. All non-essential data deleted
    2. Essential data (transactions, accounting) anonymized
    3. Account marked as deleted
    4. You will be logged out
    
    Response time: Within 1 month.
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm account deletion by setting 'confirm' to true",
        )
    
    deletion_service = DeletionService(db)
    
    # Create deletion request
    deletion_request = await deletion_service.create_deletion_request(
        user_id=current_user.id,
        reason=request.reason,
        metadata={"email": current_user.email},
    )
    
    await db.commit()
    
    # In production, this would:
    # 1. Trigger async job to delete account
    # 2. Send confirmation email
    # 3. Wait 7-day grace period (allow cancellation)
    # 4. Permanently delete/anonymize data
    # 5. Log user out
    
    logger.warning(f"User {current_user.id} requested account deletion: {deletion_request.id}")
    
    return AccountDeletionResponse(
        request_id=deletion_request.id,
        message=f"Your account deletion request has been submitted (Request ID: {deletion_request.id}). You have 7 days to cancel. After that, your account will be permanently deleted.",
    )


@router.post("/account/deletion/{request_id}/cancel")
async def cancel_account_deletion(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel pending account deletion request.
    
    Only works during grace period (7 days).
    """
    deletion_service = DeletionService(db)
    
    # In production, check if request belongs to user and is still pending
    # and within grace period
    
    # Reject the request (effectively cancelling it)
    await deletion_service.reject_deletion_request(
        request_id=request_id,
        reason="Cancelled by user",
    )
    
    await db.commit()
    
    logger.info(f"User {current_user.id} cancelled deletion request {request_id}")
    
    return {"message": "Account deletion cancelled successfully"}
