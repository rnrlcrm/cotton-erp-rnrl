"""
HSN Learning Service

Intelligent HSN code suggestion with self-learning capabilities.

Features:
- Searches local knowledge base first (instant, no API calls)
- Falls back to HSN API if configured
- Learns from user confirmations
- Improves over time
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.settings.commodities.hsn_models import HSNKnowledgeBase
from backend.modules.settings.commodities.schemas import HSNSuggestion


class HSNLearningService:
    """Self-learning HSN suggestion system"""
    
    # Development mode dummy data (used when no API configured)
    DUMMY_HSN_DATA = {
        # Textiles - Cotton
        "kapas": {"hsn": "5201", "desc": "Cotton, not carded or combed", "gst": 5.0},
        "raw cotton": {"hsn": "5201", "desc": "Cotton, not carded or combed", "gst": 5.0},
        "cotton lint": {"hsn": "5201", "desc": "Cotton, not carded or combed", "gst": 5.0},
        "cotton": {"hsn": "5201", "desc": "Cotton, not carded or combed", "gst": 5.0},
        "cotton waste": {"hsn": "5202", "desc": "Cotton waste", "gst": 5.0},
        "cotton yarn": {"hsn": "5205", "desc": "Cotton yarn containing >= 85% cotton", "gst": 5.0},
        "yarn": {"hsn": "5205", "desc": "Cotton yarn", "gst": 5.0},
        "cotton fabric": {"hsn": "5208", "desc": "Woven fabrics of cotton", "gst": 5.0},
        "fabric": {"hsn": "5208", "desc": "Woven fabrics", "gst": 5.0},
        
        # Agricultural - Seeds & Oil
        "cotton seed": {"hsn": "1207", "desc": "Oil seeds - Cotton seeds", "gst": 5.0},
        "cottonseed": {"hsn": "1207", "desc": "Oil seeds - Cotton seeds", "gst": 5.0},
        "oil cake": {"hsn": "2306", "desc": "Oil-cake and other solid residues", "gst": 5.0},
        "cotton seed oil cake": {"hsn": "2306", "desc": "Cotton seed oil-cake", "gst": 5.0},
        
        # Agricultural - Pulses
        "chana": {"hsn": "0713", "desc": "Dried leguminous vegetables - Chickpeas", "gst": 5.0},
        "chickpeas": {"hsn": "0713", "desc": "Dried leguminous vegetables - Chickpeas", "gst": 5.0},
        "dal": {"hsn": "0713", "desc": "Dried leguminous vegetables", "gst": 5.0},
        "tur dal": {"hsn": "0713", "desc": "Dried leguminous vegetables - Pigeon peas", "gst": 5.0},
        "moong dal": {"hsn": "0713", "desc": "Dried leguminous vegetables - Mung beans", "gst": 5.0},
        "urad dal": {"hsn": "0713", "desc": "Dried leguminous vegetables - Black gram", "gst": 5.0},
        "masoor dal": {"hsn": "0713", "desc": "Dried leguminous vegetables - Lentils", "gst": 5.0},
        
        # Agricultural - Grains
        "wheat": {"hsn": "1001", "desc": "Wheat and meslin", "gst": 5.0},
        "rice": {"hsn": "1006", "desc": "Rice", "gst": 5.0},
        "corn": {"hsn": "1005", "desc": "Maize (corn)", "gst": 5.0},
        "maize": {"hsn": "1005", "desc": "Maize (corn)", "gst": 5.0},
        "soybean": {"hsn": "1201", "desc": "Soya beans", "gst": 5.0},
        "soya": {"hsn": "1201", "desc": "Soya beans", "gst": 5.0},
        
        # Synthetic fibers
        "polyester": {"hsn": "5503", "desc": "Synthetic staple fibers", "gst": 18.0},
        "viscose": {"hsn": "5504", "desc": "Artificial staple fibers", "gst": 18.0},
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.hsn_api_enabled = os.getenv("HSN_API_ENABLED", "false").lower() == "true"
        self.hsn_api_key = os.getenv("HSN_API_KEY")
    
    async def suggest_hsn(
        self,
        commodity_name: str,
        category: Optional[str] = None,
        description: Optional[str] = None
    ) -> HSNSuggestion:
        """
        Suggest HSN code with learning.
        
        Order of precedence:
        1. Search knowledge base (verified entries first)
        2. Query HSN API (if configured)
        3. Use dummy data (development mode)
        4. Generic fallback
        """
        
        # 1. Search knowledge base
        learned = await self._search_knowledge_base(commodity_name, category)
        if learned:
            return learned
        
        # 2. Try HSN API (if configured)
        if self.hsn_api_enabled and self.hsn_api_key:
            api_result = await self._query_hsn_api(commodity_name, category)
            if api_result:
                # Store for future use
                await self._save_to_knowledge_base(
                    commodity_name=commodity_name,
                    category=category,
                    hsn_code=api_result.hsn_code,
                    description=api_result.description,
                    gst_rate=api_result.gst_rate,
                    source="API",
                    confidence=api_result.confidence
                )
                return api_result
        
        # 3. Use dummy data (development mode)
        dummy_result = self._get_dummy_hsn(commodity_name)
        if dummy_result:
            # Store dummy data in knowledge base for faster lookup next time
            await self._save_to_knowledge_base(
                commodity_name=commodity_name,
                category=category,
                hsn_code=dummy_result.hsn_code,
                description=dummy_result.description,
                gst_rate=dummy_result.gst_rate,
                source="SEED",
                confidence=Decimal("0.8")
            )
            return dummy_result
        
        # 4. Generic fallback
        return self._get_fallback_hsn(category)
    
    async def confirm_hsn_mapping(
        self,
        commodity_name: str,
        category: Optional[str],
        hsn_code: str,
        gst_rate: Decimal,
        description: Optional[str] = None,
        user_id: Optional[UUID] = None
    ):
        """
        User confirmed HSN mapping - store for learning.
        
        This is called when:
        - Admin creates commodity with HSN
        - Admin accepts AI suggestion
        - Admin manually corrects HSN
        """
        await self._save_to_knowledge_base(
            commodity_name=commodity_name,
            category=category,
            hsn_code=hsn_code,
            description=description,
            gst_rate=gst_rate,
            source="MANUAL",
            confidence=Decimal("1.0"),
            is_verified=True,
            user_id=user_id
        )
    
    async def _search_knowledge_base(
        self,
        commodity_name: str,
        category: Optional[str] = None
    ) -> Optional[HSNSuggestion]:
        """Search learned HSN mappings"""
        
        # Try exact match first (case-insensitive)
        query = select(HSNKnowledgeBase).where(
            func.lower(HSNKnowledgeBase.commodity_name) == commodity_name.lower()
        ).order_by(
            HSNKnowledgeBase.is_verified.desc(),  # Verified first
            HSNKnowledgeBase.confidence.desc(),   # Then by confidence
            HSNKnowledgeBase.usage_count.desc()   # Then by popularity
        ).limit(1)
        
        result = await self.db.execute(query)
        entry = result.scalar_one_or_none()
        
        if entry:
            # Increment usage count
            entry.usage_count += 1
            await self.db.commit()
            
            return HSNSuggestion(
                hsn_code=entry.hsn_code,
                description=entry.hsn_description,
                gst_rate=entry.gst_rate,
                confidence=float(entry.confidence)
            )
        
        # Try partial match if exact fails
        if len(commodity_name) > 3:
            query = select(HSNKnowledgeBase).where(
                func.lower(HSNKnowledgeBase.commodity_name).contains(commodity_name.lower())
            ).order_by(
                HSNKnowledgeBase.is_verified.desc(),
                HSNKnowledgeBase.confidence.desc()
            ).limit(1)
            
            result = await self.db.execute(query)
            entry = result.scalar_one_or_none()
            
            if entry:
                return HSNSuggestion(
                    hsn_code=entry.hsn_code,
                    description=entry.hsn_description,
                    gst_rate=entry.gst_rate,
                    confidence=float(entry.confidence) * 0.8  # Lower confidence for partial match
                )
        
        return None
    
    async def _query_hsn_api(
        self,
        commodity_name: str,
        category: Optional[str]
    ) -> Optional[HSNSuggestion]:
        """
        Query external HSN API.
        
        TODO: Implement actual API integration
        Currently returns None (API not implemented)
        """
        # Placeholder for future HSN API integration
        # Options:
        # - GST.gov.in API (official, requires auth)
        # - Masters India API (commercial)
        # - ClearTax API (commercial)
        
        return None
    
    def _get_dummy_hsn(self, commodity_name: str) -> Optional[HSNSuggestion]:
        """Get HSN from dummy data (development mode)"""
        
        # Search dummy data (case-insensitive, partial match)
        search_name = commodity_name.lower().strip()
        
        # Try exact match first
        if search_name in self.DUMMY_HSN_DATA:
            data = self.DUMMY_HSN_DATA[search_name]
            return HSNSuggestion(
                hsn_code=data["hsn"],
                description=data["desc"],
                gst_rate=Decimal(str(data["gst"])),
                confidence=0.85
            )
        
        # Try partial match
        for key, data in self.DUMMY_HSN_DATA.items():
            if key in search_name or search_name in key:
                return HSNSuggestion(
                    hsn_code=data["hsn"],
                    description=data["desc"],
                    gst_rate=Decimal(str(data["gst"])),
                    confidence=0.75  # Lower confidence for partial match
                )
        
        return None
    
    def _get_fallback_hsn(self, category: Optional[str]) -> HSNSuggestion:
        """Generic fallback when nothing else works"""
        
        # Category-based defaults
        if category:
            cat_lower = category.lower()
            if "cotton" in cat_lower or "textile" in cat_lower or "fiber" in cat_lower:
                return HSNSuggestion(
                    hsn_code="5201",
                    description="Cotton and textile products",
                    gst_rate=Decimal("5.0"),
                    confidence=0.4
                )
            elif "grain" in cat_lower or "cereal" in cat_lower:
                return HSNSuggestion(
                    hsn_code="1001",
                    description="Cereals",
                    gst_rate=Decimal("5.0"),
                    confidence=0.4
                )
            elif "pulse" in cat_lower or "dal" in cat_lower:
                return HSNSuggestion(
                    hsn_code="0713",
                    description="Dried leguminous vegetables",
                    gst_rate=Decimal("5.0"),
                    confidence=0.4
                )
        
        # Ultimate fallback
        return HSNSuggestion(
            hsn_code="0000",
            description="Please verify HSN code manually",
            gst_rate=Decimal("0.0"),
            confidence=0.0
        )
    
    async def _save_to_knowledge_base(
        self,
        commodity_name: str,
        hsn_code: str,
        gst_rate: Decimal,
        category: Optional[str] = None,
        description: Optional[str] = None,
        source: str = "MANUAL",
        confidence: Decimal = Decimal("1.0"),
        is_verified: bool = False,
        user_id: Optional[UUID] = None
    ):
        """Save learned HSN mapping to knowledge base"""
        
        # Check if entry already exists
        query = select(HSNKnowledgeBase).where(
            func.lower(HSNKnowledgeBase.commodity_name) == commodity_name.lower(),
            HSNKnowledgeBase.hsn_code == hsn_code
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing entry
            existing.gst_rate = gst_rate
            existing.confidence = max(existing.confidence, confidence)
            existing.is_verified = existing.is_verified or is_verified
            existing.usage_count += 1
            if description:
                existing.hsn_description = description
        else:
            # Create new entry
            entry = HSNKnowledgeBase(
                commodity_name=commodity_name,
                commodity_category=category,
                hsn_code=hsn_code,
                hsn_description=description,
                gst_rate=gst_rate,
                source=source,
                confidence=confidence,
                is_verified=is_verified,
                created_by=user_id
            )
            self.db.add(entry)
        
        await self.db.commit()
