"""
Commodity Module Repositories

Data access layer for all commodity-related entities.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.commodities.models import (
    BargainType,
    Commodity,
    CommodityParameter,
    CommodityVariety,
    CommissionStructure,
    DeliveryTerm,
    PassingTerm,
    PaymentTerm,
    SystemCommodityParameter,
    TradeType,
    WeightmentTerm,
)


class CommodityRepository:
    """Repository for Commodity entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> Commodity:
        """Create a new commodity"""
        commodity = Commodity(**kwargs)
        self.db.add(commodity)
        await self.db.flush()
        return commodity
    
    async def get_by_id(self, commodity_id: UUID) -> Optional[Commodity]:
        """Get commodity by ID"""
        result = await self.db.execute(
            select(Commodity).where(Commodity.id == commodity_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Commodity]:
        """Get commodity by name"""
        result = await self.db.execute(
            select(Commodity).where(Commodity.name == name)
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, skip: int = 0, limit: int = 100, category: Optional[str] = None, is_active: Optional[bool] = None) -> List[Commodity]:
        """List all commodities with filters"""
        query = select(Commodity)
        
        if category:
            query = query.where(Commodity.category == category)
        if is_active is not None:
            query = query.where(Commodity.is_active == is_active)
        
        query = query.offset(skip).limit(limit).order_by(Commodity.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, commodity_id: UUID, **kwargs) -> Optional[Commodity]:
        """Update commodity"""
        commodity = await self.get_by_id(commodity_id)
        if not commodity:
            return None
        
        for key, value in kwargs.items():
            setattr(commodity, key, value)
        
        await self.db.flush()
        return commodity
    
    async def delete(self, commodity_id: UUID) -> bool:
        """Soft delete commodity"""
        commodity = await self.get_by_id(commodity_id)
        if not commodity:
            return False
        
        commodity.is_active = False
        await self.db.flush()
        return True


class CommodityVarietyRepository:
    """Repository for CommodityVariety entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> CommodityVariety:
        """Create a new variety"""
        variety = CommodityVariety(**kwargs)
        self.db.add(variety)
        await self.db.flush()
        return variety
    
    async def get_by_id(self, variety_id: UUID) -> Optional[CommodityVariety]:
        """Get variety by ID"""
        result = await self.db.execute(
            select(CommodityVariety).where(CommodityVariety.id == variety_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_commodity(self, commodity_id: UUID) -> List[CommodityVariety]:
        """List all varieties for a commodity"""
        result = await self.db.execute(
            select(CommodityVariety)
            .where(CommodityVariety.commodity_id == commodity_id)
            .order_by(CommodityVariety.name)
        )
        return list(result.scalars().all())
    
    async def update(self, variety_id: UUID, **kwargs) -> Optional[CommodityVariety]:
        """Update variety"""
        variety = await self.get_by_id(variety_id)
        if not variety:
            return None
        
        for key, value in kwargs.items():
            setattr(variety, key, value)
        
        await self.db.flush()
        return variety
    
    async def delete(self, variety_id: UUID) -> bool:
        """Delete variety"""
        variety = await self.get_by_id(variety_id)
        if not variety:
            return False
        
        await self.db.delete(variety)
        await self.db.flush()
        return True


class CommodityParameterRepository:
    """Repository for CommodityParameter entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> CommodityParameter:
        """Create a new parameter"""
        parameter = CommodityParameter(**kwargs)
        self.db.add(parameter)
        await self.db.flush()
        return parameter
    
    async def get_by_id(self, parameter_id: UUID) -> Optional[CommodityParameter]:
        """Get parameter by ID"""
        result = await self.db.execute(
            select(CommodityParameter).where(CommodityParameter.id == parameter_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_commodity(self, commodity_id: UUID) -> List[CommodityParameter]:
        """List all parameters for a commodity"""
        result = await self.db.execute(
            select(CommodityParameter)
            .where(CommodityParameter.commodity_id == commodity_id)
            .order_by(CommodityParameter.display_order, CommodityParameter.parameter_name)
        )
        return list(result.scalars().all())
    
    async def update(self, parameter_id: UUID, **kwargs) -> Optional[CommodityParameter]:
        """Update parameter"""
        parameter = await self.get_by_id(parameter_id)
        if not parameter:
            return None
        
        for key, value in kwargs.items():
            setattr(parameter, key, value)
        
        await self.db.flush()
        return parameter
    
    async def delete(self, parameter_id: UUID) -> bool:
        """Delete parameter"""
        parameter = await self.get_by_id(parameter_id)
        if not parameter:
            return False
        
        await self.db.delete(parameter)
        await self.db.flush()
        return True


class SystemCommodityParameterRepository:
    """Repository for SystemCommodityParameter entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> SystemCommodityParameter:
        """Create a new system parameter"""
        parameter = SystemCommodityParameter(**kwargs)
        self.db.add(parameter)
        await self.db.flush()
        return parameter
    
    async def get_by_id(self, parameter_id: UUID) -> Optional[SystemCommodityParameter]:
        """Get system parameter by ID"""
        result = await self.db.execute(
            select(SystemCommodityParameter).where(SystemCommodityParameter.id == parameter_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_category(self, category: str) -> List[SystemCommodityParameter]:
        """List all system parameters for a category"""
        result = await self.db.execute(
            select(SystemCommodityParameter)
            .where(SystemCommodityParameter.commodity_category == category)
            .order_by(SystemCommodityParameter.parameter_name)
        )
        return list(result.scalars().all())
    
    async def list_all(self) -> List[SystemCommodityParameter]:
        """List all system parameters"""
        result = await self.db.execute(
            select(SystemCommodityParameter).order_by(
                SystemCommodityParameter.commodity_category,
                SystemCommodityParameter.parameter_name
            )
        )
        return list(result.scalars().all())


class TradeTypeRepository:
    """Repository for TradeType entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> TradeType:
        """Create a new trade type"""
        trade_type = TradeType(**kwargs)
        self.db.add(trade_type)
        await self.db.flush()
        return trade_type
    
    async def get_by_id(self, type_id: UUID) -> Optional[TradeType]:
        """Get trade type by ID"""
        result = await self.db.execute(
            select(TradeType).where(TradeType.id == type_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[TradeType]:
        """Get trade type by name"""
        result = await self.db.execute(
            select(TradeType).where(TradeType.name == name)
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, is_active: Optional[bool] = None) -> List[TradeType]:
        """List all trade types"""
        query = select(TradeType)
        
        if is_active is not None:
            query = query.where(TradeType.is_active == is_active)
        
        query = query.order_by(TradeType.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, type_id: UUID, **kwargs) -> Optional[TradeType]:
        """Update trade type"""
        trade_type = await self.get_by_id(type_id)
        if not trade_type:
            return None
        
        for key, value in kwargs.items():
            setattr(trade_type, key, value)
        
        await self.db.flush()
        return trade_type
    
    async def delete(self, type_id: UUID) -> bool:
        """Soft delete trade type"""
        trade_type = await self.get_by_id(type_id)
        if not trade_type:
            return False
        
        trade_type.is_active = False
        await self.db.flush()
        return True


class BargainTypeRepository:
    """Repository for BargainType entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> BargainType:
        """Create a new bargain type"""
        bargain_type = BargainType(**kwargs)
        self.db.add(bargain_type)
        await self.db.flush()
        return bargain_type
    
    async def get_by_id(self, type_id: UUID) -> Optional[BargainType]:
        """Get bargain type by ID"""
        result = await self.db.execute(
            select(BargainType).where(BargainType.id == type_id)
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, is_active: Optional[bool] = None) -> List[BargainType]:
        """List all bargain types"""
        query = select(BargainType)
        
        if is_active is not None:
            query = query.where(BargainType.is_active == is_active)
        
        query = query.order_by(BargainType.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, type_id: UUID, **kwargs) -> Optional[BargainType]:
        """Update bargain type"""
        bargain_type = await self.get_by_id(type_id)
        if not bargain_type:
            return None
        
        for key, value in kwargs.items():
            setattr(bargain_type, key, value)
        
        await self.db.flush()
        return bargain_type
    
    async def delete(self, type_id: UUID) -> bool:
        """Soft delete bargain type"""
        bargain_type = await self.get_by_id(type_id)
        if not bargain_type:
            return False
        
        bargain_type.is_active = False
        await self.db.flush()
        return True


class PassingTermRepository:
    """Repository for PassingTerm entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> PassingTerm:
        """Create a new passing term"""
        passing_term = PassingTerm(**kwargs)
        self.db.add(passing_term)
        await self.db.flush()
        return passing_term
    
    async def get_by_id(self, term_id: UUID) -> Optional[PassingTerm]:
        """Get passing term by ID"""
        result = await self.db.execute(
            select(PassingTerm).where(PassingTerm.id == term_id)
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, is_active: Optional[bool] = None) -> List[PassingTerm]:
        """List all passing terms"""
        query = select(PassingTerm)
        
        if is_active is not None:
            query = query.where(PassingTerm.is_active == is_active)
        
        query = query.order_by(PassingTerm.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, term_id: UUID, **kwargs) -> Optional[PassingTerm]:
        """Update passing term"""
        passing_term = await self.get_by_id(term_id)
        if not passing_term:
            return None
        
        for key, value in kwargs.items():
            setattr(passing_term, key, value)
        
        await self.db.flush()
        return passing_term
    
    async def delete(self, term_id: UUID) -> bool:
        """Soft delete passing term"""
        passing_term = await self.get_by_id(term_id)
        if not passing_term:
            return False
        
        passing_term.is_active = False
        await self.db.flush()
        return True


class WeightmentTermRepository:
    """Repository for WeightmentTerm entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> WeightmentTerm:
        """Create a new weightment term"""
        weightment_term = WeightmentTerm(**kwargs)
        self.db.add(weightment_term)
        await self.db.flush()
        return weightment_term
    
    async def get_by_id(self, term_id: UUID) -> Optional[WeightmentTerm]:
        """Get weightment term by ID"""
        result = await self.db.execute(
            select(WeightmentTerm).where(WeightmentTerm.id == term_id)
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, is_active: Optional[bool] = None) -> List[WeightmentTerm]:
        """List all weightment terms"""
        query = select(WeightmentTerm)
        
        if is_active is not None:
            query = query.where(WeightmentTerm.is_active == is_active)
        
        query = query.order_by(WeightmentTerm.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, term_id: UUID, **kwargs) -> Optional[WeightmentTerm]:
        """Update weightment term"""
        weightment_term = await self.get_by_id(term_id)
        if not weightment_term:
            return None
        
        for key, value in kwargs.items():
            setattr(weightment_term, key, value)
        
        await self.db.flush()
        return weightment_term
    
    async def delete(self, term_id: UUID) -> bool:
        """Soft delete weightment term"""
        weightment_term = await self.get_by_id(term_id)
        if not weightment_term:
            return False
        
        weightment_term.is_active = False
        await self.db.flush()
        return True


class DeliveryTermRepository:
    """Repository for DeliveryTerm entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> DeliveryTerm:
        """Create a new delivery term"""
        delivery_term = DeliveryTerm(**kwargs)
        self.db.add(delivery_term)
        await self.db.flush()
        return delivery_term
    
    async def get_by_id(self, term_id: UUID) -> Optional[DeliveryTerm]:
        """Get delivery term by ID"""
        result = await self.db.execute(
            select(DeliveryTerm).where(DeliveryTerm.id == term_id)
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, is_active: Optional[bool] = None) -> List[DeliveryTerm]:
        """List all delivery terms"""
        query = select(DeliveryTerm)
        
        if is_active is not None:
            query = query.where(DeliveryTerm.is_active == is_active)
        
        query = query.order_by(DeliveryTerm.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, term_id: UUID, **kwargs) -> Optional[DeliveryTerm]:
        """Update delivery term"""
        delivery_term = await self.get_by_id(term_id)
        if not delivery_term:
            return None
        
        for key, value in kwargs.items():
            setattr(delivery_term, key, value)
        
        await self.db.flush()
        return delivery_term
    
    async def delete(self, term_id: UUID) -> bool:
        """Soft delete delivery term"""
        delivery_term = await self.get_by_id(term_id)
        if not delivery_term:
            return False
        
        delivery_term.is_active = False
        await self.db.flush()
        return True


class PaymentTermRepository:
    """Repository for PaymentTerm entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> PaymentTerm:
        """Create a new payment term"""
        payment_term = PaymentTerm(**kwargs)
        self.db.add(payment_term)
        await self.db.flush()
        return payment_term
    
    async def get_by_id(self, term_id: UUID) -> Optional[PaymentTerm]:
        """Get payment term by ID"""
        result = await self.db.execute(
            select(PaymentTerm).where(PaymentTerm.id == term_id)
        )
        return result.scalar_one_or_none()
    
    async def list_all(self, is_active: Optional[bool] = None) -> List[PaymentTerm]:
        """List all payment terms"""
        query = select(PaymentTerm)
        
        if is_active is not None:
            query = query.where(PaymentTerm.is_active == is_active)
        
        query = query.order_by(PaymentTerm.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, term_id: UUID, **kwargs) -> Optional[PaymentTerm]:
        """Update payment term"""
        payment_term = await self.get_by_id(term_id)
        if not payment_term:
            return None
        
        for key, value in kwargs.items():
            setattr(payment_term, key, value)
        
        await self.db.flush()
        return payment_term
    
    async def delete(self, term_id: UUID) -> bool:
        """Soft delete payment term"""
        payment_term = await self.get_by_id(term_id)
        if not payment_term:
            return False
        
        payment_term.is_active = False
        await self.db.flush()
        return True


class CommissionStructureRepository:
    """Repository for CommissionStructure entity"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, **kwargs) -> CommissionStructure:
        """Create a new commission structure"""
        commission = CommissionStructure(**kwargs)
        self.db.add(commission)
        await self.db.flush()
        return commission
    
    async def get_by_id(self, commission_id: UUID) -> Optional[CommissionStructure]:
        """Get commission by ID"""
        result = await self.db.execute(
            select(CommissionStructure).where(CommissionStructure.id == commission_id)
        )
        return result.scalar_one_or_none()
    
    async def list_all(
        self, 
        commodity_id: Optional[UUID] = None,
        trade_type_id: Optional[UUID] = None,
        is_active: Optional[bool] = None
    ) -> List[CommissionStructure]:
        """List all commissions with filters"""
        query = select(CommissionStructure)
        
        if commodity_id:
            query = query.where(CommissionStructure.commodity_id == commodity_id)
        if trade_type_id:
            query = query.where(CommissionStructure.trade_type_id == trade_type_id)
        if is_active is not None:
            query = query.where(CommissionStructure.is_active == is_active)
        
        query = query.order_by(CommissionStructure.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, commission_id: UUID, **kwargs) -> Optional[CommissionStructure]:
        """Update commission"""
        commission = await self.get_by_id(commission_id)
        if not commission:
            return None
        
        for key, value in kwargs.items():
            setattr(commission, key, value)
        
        await self.db.flush()
        return commission
    
    async def delete(self, commission_id: UUID) -> bool:
        """Soft delete commission"""
        commission = await self.get_by_id(commission_id)
        if not commission:
            return False
        
        commission.is_active = False
        await self.db.flush()
        return True
