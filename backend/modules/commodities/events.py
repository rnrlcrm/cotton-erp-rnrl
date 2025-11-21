"""
Commodity Module Events

Defines all events that can occur in the commodity module.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from backend.core.events.base import BaseEvent, EventMetadata


class CommodityCreated(BaseEvent):
    """Emitted when a new commodity is created"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.created",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class CommodityUpdated(BaseEvent):
    """Emitted when commodity details are updated"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],  # Should include 'changes' dict
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.updated",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class CommodityDeleted(BaseEvent):
    """Emitted when commodity is soft-deleted"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.deleted",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class CommodityVarietyAdded(BaseEvent):
    """Emitted when a new variety is added to a commodity"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # commodity_id
        user_id: uuid.UUID,
        data: Dict[str, Any],  # variety details
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.variety.added",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class CommodityVarietyUpdated(BaseEvent):
    """Emitted when a variety is updated"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.variety.updated",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class CommodityParameterAdded(BaseEvent):
    """Emitted when a quality parameter is added"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.parameter.added",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class CommodityParameterUpdated(BaseEvent):
    """Emitted when a parameter is updated"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.parameter.updated",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class CommissionStructureSet(BaseEvent):
    """Emitted when commission structure is set/updated"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,  # commodity_id or generic UUID
        user_id: uuid.UUID,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.commission.set",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class TradeTermsCreated(BaseEvent):
    """Emitted when trade terms (any type) are created"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],  # Include term_type: trade/bargain/passing/etc
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="trade_terms.created",
            aggregate_id=aggregate_id,
            aggregate_type="trade_terms",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )


class TradeTermsUpdated(BaseEvent):
    """Emitted when trade terms are updated"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="trade_terms.updated",
            aggregate_id=aggregate_id,
            aggregate_type="trade_terms",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )
