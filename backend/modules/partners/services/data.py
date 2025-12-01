"""
Partner Data Service

Handles all repository operations for partners router.
This service centralizes all database access to maintain clean architecture.

Extracted from router to ensure:
- No direct repository instantiations in routers
- All business logic in service layer
- Proper event handling through outbox pattern
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.outbox import OutboxRepository
from backend.modules.partners.repositories import (
    BusinessPartnerRepository,
    OnboardingApplicationRepository,
    PartnerDocumentRepository,
    PartnerEmployeeRepository,
    PartnerLocationRepository,
    PartnerVehicleRepository,
    PartnerAmendmentRepository,
)
from backend.modules.partners.models import (
    BusinessPartner,
    PartnerOnboardingApplication,
    PartnerDocument,
    PartnerEmployee,
    PartnerLocation,
    PartnerVehicle,
)
from backend.modules.partners.enums import DocumentType


class PartnerDataService:
    """
    Service for partner data access operations.
    
    This service handles:
    - Application retrieval
    - Partner CRUD operations  
    - Location management
    - Employee management
    - Vehicle management
    - Document access
    """
    
    def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client
        self.outbox_repo = OutboxRepository(db)
        
        # Initialize repositories
        self.app_repo = OnboardingApplicationRepository(db)
        self.partner_repo = BusinessPartnerRepository(db)
        self.doc_repo = PartnerDocumentRepository(db)
        self.location_repo = PartnerLocationRepository(db)
        self.employee_repo = PartnerEmployeeRepository(db)
        self.vehicle_repo = PartnerVehicleRepository(db)
        self.amendment_repo = PartnerAmendmentRepository(db)
    
    # ===== APPLICATION OPERATIONS =====
    
    async def get_application(
        self,
        application_id: UUID,
        organization_id: UUID
    ) -> Optional[PartnerOnboardingApplication]:
        """Get onboarding application by ID."""
        return await self.app_repo.get_by_id(application_id, organization_id)
    
    # ===== PARTNER OPERATIONS =====
    
    async def get_partner(
        self,
        partner_id: UUID,
        organization_id: UUID
    ) -> Optional[BusinessPartner]:
        """Get partner by ID."""
        return await self.partner_repo.get_by_id(partner_id, organization_id)
    
    async def list_partners(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[BusinessPartner]:
        """List partners with optional filters."""
        return await self.partner_repo.list_all(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            **filters
        )
    
    # ===== LOCATION OPERATIONS =====
    
    async def create_location(
        self,
        partner_id: UUID,
        organization_id: UUID,
        **location_data
    ) -> PartnerLocation:
        """Create a new location for partner."""
        return await self.location_repo.create(
            partner_id=partner_id,
            organization_id=organization_id,
            **location_data
        )
    
    async def get_location(
        self,
        location_id: UUID,
        organization_id: UUID
    ) -> Optional[PartnerLocation]:
        """Get location by ID."""
        return await self.location_repo.get_by_id(location_id, organization_id)
    
    async def update_location(
        self,
        location_id: UUID,
        organization_id: UUID,
        **update_data
    ) -> PartnerLocation:
        """Update location."""
        return await self.location_repo.update(
            location_id=location_id,
            organization_id=organization_id,
            **update_data
        )
    
    # ===== EMPLOYEE OPERATIONS =====
    
    async def create_employee(
        self,
        partner_id: UUID,
        organization_id: UUID,
        **employee_data
    ) -> PartnerEmployee:
        """Create employee for partner."""
        return await self.employee_repo.create(
            partner_id=partner_id,
            organization_id=organization_id,
            **employee_data
        )
    
    # ===== DOCUMENT OPERATIONS =====
    
    async def create_document(
        self,
        partner_id: UUID,
        organization_id: UUID,
        document_type: DocumentType,
        **document_data
    ) -> PartnerDocument:
        """Create document for partner."""
        return await self.doc_repo.create(
            partner_id=partner_id,
            organization_id=organization_id,
            document_type=document_type,
            **document_data
        )
    
    async def get_partner_documents(
        self,
        partner_id: UUID,
        organization_id: UUID
    ) -> List[PartnerDocument]:
        """Get all documents for a partner."""
        return await self.doc_repo.get_by_partner(
            partner_id=partner_id,
            organization_id=organization_id
        )
    
    # ===== VEHICLE OPERATIONS =====
    
    async def create_vehicle(
        self,
        partner_id: UUID,
        organization_id: UUID,
        **vehicle_data
    ) -> PartnerVehicle:
        """Create vehicle for partner."""
        return await self.vehicle_repo.create(
            partner_id=partner_id,
            organization_id=organization_id,
            **vehicle_data
        )
    
    async def get_partner_vehicles(
        self,
        partner_id: UUID,
        organization_id: UUID
    ) -> List[PartnerVehicle]:
        """Get all vehicles for a partner."""
        return await self.vehicle_repo.get_by_partner(
            partner_id=partner_id,
            organization_id=organization_id
        )
    
    # ===== EXPORT OPERATIONS =====
    
    async def get_export_data(
        self,
        organization_id: UUID,
        **filters
    ) -> List[BusinessPartner]:
        """
        Get partners for export with filters.
        Delegates to partner repository.
        """
        return await self.partner_repo.list_all(
            organization_id=organization_id,
            **filters
        )
