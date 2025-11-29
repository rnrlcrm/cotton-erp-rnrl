"""
Partner Analytics Service

Handles all analytics, reporting, and dashboard queries for partners.
Extracted from router to maintain clean architecture for 15 years.

NO business logic changes - pure extraction.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.partners.models import BusinessPartner
from backend.modules.partners.enums import PartnerStatus, PartnerType, KYCStatus, RiskCategory


class PartnerAnalyticsService:
    """
    Service for partner analytics and reporting.
    
    This service handles:
    - Dashboard statistics
    - Trend analysis
    - Export data preparation
    - Geographic distribution
    - Risk distribution
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_dashboard_stats(self, organization_id: UUID) -> Dict[str, Any]:
        """
        Get dashboard statistics for partners.
        
        Returns:
            Dictionary with counts by type, status, risk, state, and monthly trends
        """
        # Count by partner type
        by_type_query = select(
            BusinessPartner.partner_type,
            func.count(BusinessPartner.id).label('count')
        ).where(
            and_(
                BusinessPartner.organization_id == organization_id,
                BusinessPartner.is_deleted == False
            )
        ).group_by(BusinessPartner.partner_type)
        
        by_type_result = await self.db.execute(by_type_query)
        by_type = {row.partner_type: row.count for row in by_type_result}
        
        # Count by status
        by_status_query = select(
            BusinessPartner.status,
            func.count(BusinessPartner.id).label('count')
        ).where(
            and_(
                BusinessPartner.organization_id == organization_id,
                BusinessPartner.is_deleted == False
            )
        ).group_by(BusinessPartner.status)
        
        by_status_result = await self.db.execute(by_status_query)
        by_status = {row.status: row.count for row in by_status_result}
        
        # Count expiring KYC (next 30 days)
        expiring_kyc_query = select(func.count(BusinessPartner.id)).where(
            and_(
                BusinessPartner.organization_id == organization_id,
                BusinessPartner.is_deleted == False,
                BusinessPartner.kyc_expiry_date.between(
                    datetime.utcnow(),
                    datetime.utcnow() + timedelta(days=30)
                )
            )
        )
        expiring_kyc_result = await self.db.execute(expiring_kyc_query)
        expiring_kyc_count = expiring_kyc_result.scalar() or 0
        
        # High risk partners
        high_risk_query = select(func.count(BusinessPartner.id)).where(
            and_(
                BusinessPartner.organization_id == organization_id,
                BusinessPartner.is_deleted == False,
                BusinessPartner.risk_category == RiskCategory.HIGH
            )
        )
        high_risk_result = await self.db.execute(high_risk_query)
        high_risk_count = high_risk_result.scalar() or 0
        
        # Risk distribution
        risk_query = select(
            BusinessPartner.risk_category,
            func.count(BusinessPartner.id).label('count')
        ).where(
            and_(
                BusinessPartner.organization_id == organization_id,
                BusinessPartner.is_deleted == False,
                BusinessPartner.risk_category.isnot(None)
            )
        ).group_by(BusinessPartner.risk_category)
        
        risk_result = await self.db.execute(risk_query)
        risk_distribution = {row.risk_category: row.count for row in risk_result}
        
        # State distribution (top 10)
        state_query = select(
            BusinessPartner.primary_state,
            func.count(BusinessPartner.id).label('count')
        ).where(
            and_(
                BusinessPartner.organization_id == organization_id,
                BusinessPartner.is_deleted == False,
                BusinessPartner.primary_state.isnot(None)
            )
        ).group_by(BusinessPartner.primary_state).order_by(desc('count')).limit(10)
        
        state_result = await self.db.execute(state_query)
        state_distribution = {row.primary_state: row.count for row in state_result}
        
        # Monthly onboarding trend (last 12 months)
        monthly_query = select(
            func.date_trunc('month', BusinessPartner.created_at).label('month'),
            func.count(BusinessPartner.id).label('count')
        ).where(
            and_(
                BusinessPartner.organization_id == organization_id,
                BusinessPartner.is_deleted == False,
                BusinessPartner.created_at >= datetime.utcnow() - timedelta(days=365)
            )
        ).group_by('month').order_by('month')
        
        monthly_result = await self.db.execute(monthly_query)
        monthly_trend = [
            {"month": row.month.isoformat(), "count": row.count}
            for row in monthly_result
        ]
        
        return {
            "by_type": by_type,
            "by_status": by_status,
            "expiring_kyc_count": expiring_kyc_count,
            "high_risk_count": high_risk_count,
            "risk_distribution": risk_distribution,
            "state_distribution": state_distribution,
            "monthly_trend": monthly_trend,
        }
    
    async def get_export_data(
        self,
        organization_id: UUID,
        partner_type: Optional[PartnerType] = None,
        status: Optional[PartnerStatus] = None,
        kyc_status: Optional[KYCStatus] = None,
        state: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[BusinessPartner]:
        """
        Get partners for export (Excel/CSV).
        
        Returns:
            List of partner records matching filters
        """
        query = select(BusinessPartner).where(
            BusinessPartner.organization_id == organization_id,
            BusinessPartner.is_deleted == False
        )
        
        if partner_type:
            query = query.where(BusinessPartner.partner_type == partner_type)
        if status:
            query = query.where(BusinessPartner.status == status)
        if kyc_status:
            query = query.where(BusinessPartner.kyc_status == kyc_status)
        if state:
            query = query.where(BusinessPartner.primary_state == state)
        if date_from:
            query = query.where(BusinessPartner.created_at >= date_from)
        if date_to:
            query = query.where(BusinessPartner.created_at <= date_to)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_kyc_expiring_partners(
        self,
        organization_id: UUID,
        days_ahead: int = 30
    ) -> List[BusinessPartner]:
        """
        Get partners with KYC expiring soon.
        
        Args:
            organization_id: Organization ID
            days_ahead: How many days to look ahead
            
        Returns:
            List of partners with expiring KYC
        """
        expiry_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        query = select(BusinessPartner).where(
            and_(
                BusinessPartner.organization_id == organization_id,
                BusinessPartner.is_deleted == False,
                BusinessPartner.kyc_expiry_date <= expiry_date,
                BusinessPartner.kyc_expiry_date >= datetime.utcnow()
            )
        ).order_by(BusinessPartner.kyc_expiry_date)
        
        result = await self.db.execute(query)
        return result.scalars().all()
