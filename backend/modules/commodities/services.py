"""
Commodity Services

Business logic layer with event sourcing for commodity management.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events.emitter import EventEmitter
from backend.modules.commodities.ai_helpers import CommodityAIHelper
from backend.modules.commodities.events import (
    CommodityCreated,
    CommodityDeleted,
    CommodityParameterAdded,
    CommodityParameterUpdated,
    CommodityUpdated,
    CommodityVarietyAdded,
    CommodityVarietyUpdated,
    CommissionStructureSet,
    TradeTermsCreated,
    TradeTermsUpdated,
)
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
from backend.modules.commodities.repositories import (
    BargainTypeRepository,
    CommodityParameterRepository,
    CommodityRepository,
    CommodityVarietyRepository,
    CommissionStructureRepository,
    DeliveryTermRepository,
    PassingTermRepository,
    PaymentTermRepository,
    SystemCommodityParameterRepository,
    TradeTypeRepository,
    WeightmentTermRepository,
)
from backend.modules.commodities.schemas import (
    BargainTypeCreate,
    BargainTypeUpdate,
    CommodityCreate,
    CommodityParameterCreate,
    CommodityParameterUpdate,
    CommodityUpdate,
    CommodityVarietyCreate,
    CommodityVarietyUpdate,
    CommissionStructureCreate,
    CommissionStructureUpdate,
    DeliveryTermCreate,
    DeliveryTermUpdate,
    PassingTermCreate,
    PassingTermUpdate,
    PaymentTermCreate,
    PaymentTermUpdate,
    SystemCommodityParameterCreate,
    SystemCommodityParameterUpdate,
    TradeTypeCreate,
    TradeTypeUpdate,
    WeightmentTermCreate,
    WeightmentTermUpdate,
)


class CommodityService:
    """Service for commodity operations with event sourcing"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        ai_helper: CommodityAIHelper,
        current_user_id: UUID
    ):
        self.repository = CommodityRepository(session)
        self.event_emitter = event_emitter
        self.ai_helper = ai_helper
        self.current_user_id = current_user_id
    
    async def create_commodity(self, data: CommodityCreate) -> Commodity:
        """Create new commodity with AI enrichment and event emission"""
        
        # AI enrichment if needed
        if not data.hsn_code or not data.gst_rate:
            enrichment = await self.ai_helper.enrich_commodity_data(
                name=data.name,
                category=data.category,
                description=data.description
            )
            
            if not data.hsn_code:
                data.hsn_code = enrichment["suggested_hsn_code"]
            if not data.gst_rate:
                data.gst_rate = enrichment["suggested_gst_rate"]
        
        # Create commodity
        commodity = await self.repository.create(data)
        
        # Emit event
        await self.event_emitter.emit(
            CommodityCreated(
                entity_type="Commodity",
                entity_id=commodity.id,
                user_id=self.current_user_id,
                payload={
                    "name": commodity.name,
                    "category": commodity.category,
                    "hsn_code": commodity.hsn_code,
                    "gst_rate": str(commodity.gst_rate) if commodity.gst_rate else None
                }
            )
        )
        
        return commodity
    
    async def update_commodity(
        self,
        commodity_id: UUID,
        data: CommodityUpdate
    ) -> Optional[Commodity]:
        """Update commodity and emit event"""
        
        # Get existing
        existing = await self.repository.get_by_id(commodity_id)
        if not existing:
            return None
        
        # Update
        commodity = await self.repository.update(commodity_id, data)
        if not commodity:
            return None
        
        # Emit event
        changes = {}
        for field in ["name", "category", "hsn_code", "gst_rate", "is_active"]:
            old_value = getattr(existing, field)
            new_value = getattr(commodity, field)
            if old_value != new_value:
                changes[field] = {
                    "old": str(old_value) if old_value is not None else None,
                    "new": str(new_value) if new_value is not None else None
                }
        
        await self.event_emitter.emit(
            CommodityUpdated(
                entity_type="Commodity",
                entity_id=commodity.id,
                user_id=self.current_user_id,
                payload={"changes": changes}
            )
        )
        
        return commodity
    
    async def delete_commodity(self, commodity_id: UUID) -> bool:
        """Delete commodity and emit event"""
        
        commodity = await self.repository.get_by_id(commodity_id)
        if not commodity:
            return False
        
        success = await self.repository.delete(commodity_id)
        
        if success:
            await self.event_emitter.emit(
                CommodityDeleted(
                    entity_type="Commodity",
                    entity_id=commodity_id,
                    user_id=self.current_user_id,
                    payload={"name": commodity.name}
                )
            )
        
        return success
    
    async def get_commodity(self, commodity_id: UUID) -> Optional[Commodity]:
        """Get commodity by ID"""
        return await self.repository.get_by_id(commodity_id)
    
    async def list_commodities(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Commodity]:
        """List commodities with optional filters"""
        return await self.repository.list_all(category=category, is_active=is_active)


class CommodityVarietyService:
    """Service for commodity variety operations"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = CommodityVarietyRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def add_variety(self, data: CommodityVarietyCreate) -> CommodityVariety:
        """Add variety to commodity"""
        
        variety = await self.repository.create(data)
        
        await self.event_emitter.emit(
            CommodityVarietyAdded(
                entity_type="CommodityVariety",
                entity_id=variety.id,
                user_id=self.current_user_id,
                payload={
                    "commodity_id": str(variety.commodity_id),
                    "name": variety.name,
                    "code": variety.code
                }
            )
        )
        
        return variety
    
    async def update_variety(
        self,
        variety_id: UUID,
        data: CommodityVarietyUpdate
    ) -> Optional[CommodityVariety]:
        """Update variety"""
        
        variety = await self.repository.update(variety_id, data)
        if not variety:
            return None
        
        await self.event_emitter.emit(
            CommodityVarietyUpdated(
                entity_type="CommodityVariety",
                entity_id=variety.id,
                user_id=self.current_user_id,
                payload={"variety_name": variety.name}
            )
        )
        
        return variety
    
    async def list_varieties(
        self,
        commodity_id: Optional[UUID] = None
    ) -> List[CommodityVariety]:
        """List varieties"""
        return await self.repository.list_all(commodity_id=commodity_id)


class CommodityParameterService:
    """Service for commodity quality parameters"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = CommodityParameterRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def add_parameter(
        self,
        data: CommodityParameterCreate
    ) -> CommodityParameter:
        """Add quality parameter to commodity"""
        
        parameter = await self.repository.create(data)
        
        await self.event_emitter.emit(
            CommodityParameterAdded(
                entity_type="CommodityParameter",
                entity_id=parameter.id,
                user_id=self.current_user_id,
                payload={
                    "commodity_id": str(parameter.commodity_id),
                    "name": parameter.name,
                    "type": parameter.type
                }
            )
        )
        
        return parameter
    
    async def update_parameter(
        self,
        parameter_id: UUID,
        data: CommodityParameterUpdate
    ) -> Optional[CommodityParameter]:
        """Update parameter"""
        
        parameter = await self.repository.update(parameter_id, data)
        if not parameter:
            return None
        
        await self.event_emitter.emit(
            CommodityParameterUpdated(
                entity_type="CommodityParameter",
                entity_id=parameter.id,
                user_id=self.current_user_id,
                payload={"parameter_name": parameter.name}
            )
        )
        
        return parameter
    
    async def list_parameters(
        self,
        commodity_id: Optional[UUID] = None
    ) -> List[CommodityParameter]:
        """List parameters"""
        return await self.repository.list_all(commodity_id=commodity_id)


class SystemCommodityParameterService:
    """Service for system-wide commodity parameters (AI training data)"""
    
    def __init__(self, session: AsyncSession):
        self.repository = SystemCommodityParameterRepository(session)
    
    async def create_parameter(
        self,
        data: SystemCommodityParameterCreate
    ) -> SystemCommodityParameter:
        """Create system parameter"""
        return await self.repository.create(data)
    
    async def update_parameter(
        self,
        parameter_id: UUID,
        data: SystemCommodityParameterUpdate
    ) -> Optional[SystemCommodityParameter]:
        """Update system parameter"""
        return await self.repository.update(parameter_id, data)
    
    async def list_parameters(
        self,
        category: Optional[str] = None
    ) -> List[SystemCommodityParameter]:
        """List system parameters"""
        return await self.repository.list_all(category=category)


class TradeTypeService:
    """Service for trade type operations"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = TradeTypeRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def create_trade_type(self, data: TradeTypeCreate) -> TradeType:
        """Create trade type"""
        
        trade_type = await self.repository.create(data)
        
        await self.event_emitter.emit(
            TradeTermsCreated(
                entity_type="TradeType",
                entity_id=trade_type.id,
                user_id=self.current_user_id,
                payload={
                    "term_type": "Trade Type",
                    "name": trade_type.name
                }
            )
        )
        
        return trade_type
    
    async def update_trade_type(
        self,
        trade_type_id: UUID,
        data: TradeTypeUpdate
    ) -> Optional[TradeType]:
        """Update trade type"""
        
        trade_type = await self.repository.update(trade_type_id, data)
        if not trade_type:
            return None
        
        await self.event_emitter.emit(
            TradeTermsUpdated(
                entity_type="TradeType",
                entity_id=trade_type.id,
                user_id=self.current_user_id,
                payload={
                    "term_type": "Trade Type",
                    "name": trade_type.name
                }
            )
        )
        
        return trade_type
    
    async def list_trade_types(self) -> List[TradeType]:
        """List all trade types"""
        return await self.repository.list_all()


class BargainTypeService:
    """Service for bargain type operations"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = BargainTypeRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def create_bargain_type(self, data: BargainTypeCreate) -> BargainType:
        """Create bargain type"""
        
        bargain_type = await self.repository.create(data)
        
        await self.event_emitter.emit(
            TradeTermsCreated(
                entity_type="BargainType",
                entity_id=bargain_type.id,
                user_id=self.current_user_id,
                payload={
                    "term_type": "Bargain Type",
                    "name": bargain_type.name
                }
            )
        )
        
        return bargain_type
    
    async def update_bargain_type(
        self,
        bargain_type_id: UUID,
        data: BargainTypeUpdate
    ) -> Optional[BargainType]:
        """Update bargain type"""
        
        bargain_type = await self.repository.update(bargain_type_id, data)
        if not bargain_type:
            return None
        
        await self.event_emitter.emit(
            TradeTermsUpdated(
                entity_type="BargainType",
                entity_id=bargain_type.id,
                user_id=self.current_user_id,
                payload={
                    "term_type": "Bargain Type",
                    "name": bargain_type.name
                }
            )
        )
        
        return bargain_type
    
    async def list_bargain_types(self) -> List[BargainType]:
        """List all bargain types"""
        return await self.repository.list_all()


class PassingTermService:
    """Service for passing term operations"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = PassingTermRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def create_passing_term(self, data: PassingTermCreate) -> PassingTerm:
        """Create passing term"""
        term = await self.repository.create(data)
        
        await self.event_emitter.emit(
            TradeTermsCreated(
                entity_type="PassingTerm",
                entity_id=term.id,
                user_id=self.current_user_id,
                payload={"term_type": "Passing", "name": term.name}
            )
        )
        
        return term
    
    async def update_passing_term(
        self,
        term_id: UUID,
        data: PassingTermUpdate
    ) -> Optional[PassingTerm]:
        """Update passing term"""
        term = await self.repository.update(term_id, data)
        if term:
            await self.event_emitter.emit(
                TradeTermsUpdated(
                    entity_type="PassingTerm",
                    entity_id=term.id,
                    user_id=self.current_user_id,
                    payload={"term_type": "Passing", "name": term.name}
                )
            )
        return term
    
    async def list_passing_terms(self) -> List[PassingTerm]:
        """List all passing terms"""
        return await self.repository.list_all()


class WeightmentTermService:
    """Service for weightment term operations"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = WeightmentTermRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def create_weightment_term(
        self,
        data: WeightmentTermCreate
    ) -> WeightmentTerm:
        """Create weightment term"""
        term = await self.repository.create(data)
        
        await self.event_emitter.emit(
            TradeTermsCreated(
                entity_type="WeightmentTerm",
                entity_id=term.id,
                user_id=self.current_user_id,
                payload={"term_type": "Weightment", "name": term.name}
            )
        )
        
        return term
    
    async def update_weightment_term(
        self,
        term_id: UUID,
        data: WeightmentTermUpdate
    ) -> Optional[WeightmentTerm]:
        """Update weightment term"""
        term = await self.repository.update(term_id, data)
        if term:
            await self.event_emitter.emit(
                TradeTermsUpdated(
                    entity_type="WeightmentTerm",
                    entity_id=term.id,
                    user_id=self.current_user_id,
                    payload={"term_type": "Weightment", "name": term.name}
                )
            )
        return term
    
    async def list_weightment_terms(self) -> List[WeightmentTerm]:
        """List all weightment terms"""
        return await self.repository.list_all()


class DeliveryTermService:
    """Service for delivery term operations"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = DeliveryTermRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def create_delivery_term(self, data: DeliveryTermCreate) -> DeliveryTerm:
        """Create delivery term"""
        term = await self.repository.create(data)
        
        await self.event_emitter.emit(
            TradeTermsCreated(
                entity_type="DeliveryTerm",
                entity_id=term.id,
                user_id=self.current_user_id,
                payload={"term_type": "Delivery", "name": term.name}
            )
        )
        
        return term
    
    async def update_delivery_term(
        self,
        term_id: UUID,
        data: DeliveryTermUpdate
    ) -> Optional[DeliveryTerm]:
        """Update delivery term"""
        term = await self.repository.update(term_id, data)
        if term:
            await self.event_emitter.emit(
                TradeTermsUpdated(
                    entity_type="DeliveryTerm",
                    entity_id=term.id,
                    user_id=self.current_user_id,
                    payload={"term_type": "Delivery", "name": term.name}
                )
            )
        return term
    
    async def list_delivery_terms(self) -> List[DeliveryTerm]:
        """List all delivery terms"""
        return await self.repository.list_all()


class PaymentTermService:
    """Service for payment term operations"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = PaymentTermRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def create_payment_term(self, data: PaymentTermCreate) -> PaymentTerm:
        """Create payment term"""
        term = await self.repository.create(data)
        
        await self.event_emitter.emit(
            TradeTermsCreated(
                entity_type="PaymentTerm",
                entity_id=term.id,
                user_id=self.current_user_id,
                payload={"term_type": "Payment", "name": term.name}
            )
        )
        
        return term
    
    async def update_payment_term(
        self,
        term_id: UUID,
        data: PaymentTermUpdate
    ) -> Optional[PaymentTerm]:
        """Update payment term"""
        term = await self.repository.update(term_id, data)
        if term:
            await self.event_emitter.emit(
                TradeTermsUpdated(
                    entity_type="PaymentTerm",
                    entity_id=term.id,
                    user_id=self.current_user_id,
                    payload={"term_type": "Payment", "name": term.name}
                )
            )
        return term
    
    async def list_payment_terms(self) -> List[PaymentTerm]:
        """List all payment terms"""
        return await self.repository.list_all()


class CommissionStructureService:
    """Service for commission structure operations"""
    
    def __init__(
        self,
        session: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID
    ):
        self.repository = CommissionStructureRepository(session)
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
    
    async def set_commission(
        self,
        data: CommissionStructureCreate
    ) -> CommissionStructure:
        """Set commission structure for commodity"""
        
        commission = await self.repository.create(data)
        
        await self.event_emitter.emit(
            CommissionStructureSet(
                entity_type="CommissionStructure",
                entity_id=commission.id,
                user_id=self.current_user_id,
                payload={
                    "commodity_id": str(commission.commodity_id),
                    "broker_commission": str(commission.broker_commission),
                    "sub_broker_commission": str(commission.sub_broker_commission)
                }
            )
        )
        
        return commission
    
    async def update_commission(
        self,
        commission_id: UUID,
        data: CommissionStructureUpdate
    ) -> Optional[CommissionStructure]:
        """Update commission structure"""
        
        commission = await self.repository.update(commission_id, data)
        if not commission:
            return None
        
        await self.event_emitter.emit(
            CommissionStructureSet(
                entity_type="CommissionStructure",
                entity_id=commission.id,
                user_id=self.current_user_id,
                payload={
                    "commodity_id": str(commission.commodity_id),
                    "broker_commission": str(commission.broker_commission),
                    "sub_broker_commission": str(commission.sub_broker_commission)
                }
            )
        )
        
        return commission
    
    async def get_commission(
        self,
        commodity_id: UUID
    ) -> Optional[CommissionStructure]:
        """Get commission for commodity"""
        commissions = await self.repository.list_all(commodity_id=commodity_id)
        return commissions[0] if commissions else None
