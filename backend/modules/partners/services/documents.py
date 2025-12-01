"""
Partner Document Service

Handles document upload, processing, and management for partners.
Extracted from router to maintain clean architecture for 15 years.

NO business logic changes - pure extraction.
"""

from typing import List, Optional, Literal
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.outbox import OutboxRepository
from backend.modules.partners.repositories import PartnerDocumentRepository
from backend.modules.partners.models import PartnerDocument
from backend.modules.partners.enums import DocumentType

# Document status literals (not enum - stored as strings)
DocumentStatusType = Literal["pending", "approved", "rejected", "expired"]


class PartnerDocumentService:
    """
    Service for partner document management.
    
    This service handles:
    - Document upload
    - Document validation
    - Document status tracking
    - Document retrieval
    """
    
    def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client
        self.outbox_repo = OutboxRepository(db)
        self.document_repo = PartnerDocumentRepository(db)
    
    async def upload_document(
        self,
        partner_id: UUID,
        document_type: DocumentType,
        file: UploadFile,
        uploaded_by: UUID,
    ) -> PartnerDocument:
        """
        Upload a document for a partner.
        
        Args:
            partner_id: Partner ID
            document_type: Type of document
            file: Uploaded file
            uploaded_by: User ID who uploaded
            
        Returns:
            Created document record
        """
        # Read file content
        file_content = await file.read()
        
        # Create document record
        document = await self.document_repo.create(
            partner_id=partner_id,
            document_type=document_type,
            file_name=file.filename,
            file_size=len(file_content),
            file_content=file_content,
            uploaded_by=uploaded_by,
            status="pending",
        )
        
        return document
    
    async def get_partner_documents(
        self,
        partner_id: UUID,
        document_type: Optional[DocumentType] = None,
    ) -> List[PartnerDocument]:
        """
        Get all documents for a partner.
        
        Args:
            partner_id: Partner ID
            document_type: Optional filter by document type
            
        Returns:
            List of documents
        """
        return await self.document_repo.get_by_partner(
            partner_id=partner_id,
            document_type=document_type,
        )
    
    async def get_document(self, document_id: UUID) -> Optional[PartnerDocument]:
        """Get a single document by ID."""
        return await self.document_repo.get_by_id(document_id)
    
    async def update_document_status(
        self,
        document_id: UUID,
        status: DocumentStatusType,
        verified_by: Optional[UUID] = None,
        rejection_reason: Optional[str] = None,
    ) -> PartnerDocument:
        """
        Update document verification status.
        
        Args:
            document_id: Document ID
            status: New status
            verified_by: User who verified (for approved/rejected)
            rejection_reason: Reason for rejection
            
        Returns:
            Updated document
        """
        return await self.document_repo.update_status(
            document_id=document_id,
            status=status,
            verified_by=verified_by,
            rejection_reason=rejection_reason,
        )
    
    async def check_all_documents_verified(self, partner_id: UUID) -> bool:
        """
        Check if all required documents are verified.
        
        Returns:
            True if all required documents are approved
        """
        documents = await self.document_repo.get_by_partner(partner_id)
        
        # Required document types (adjust based on business rules)
        required_types = {
            DocumentType.GST_CERTIFICATE,
            DocumentType.PAN_CARD,
            DocumentType.ADDRESS_PROOF,
        }
        
        # Check if all required types are approved
        approved_types = {
            doc.document_type
            for doc in documents
            if doc.status == DocumentStatus.APPROVED
        }
        
        return required_types.issubset(approved_types)
