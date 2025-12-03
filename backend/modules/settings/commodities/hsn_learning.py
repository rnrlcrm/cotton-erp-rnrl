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
    
    # Constants
    DESC_COTTON_RAW = "Cotton, not carded or combed"
    
    # Development mode dummy data (used when no API configured)
    DUMMY_HSN_DATA = {
        # Textiles - Cotton
        "kapas": {"hsn": "5201", "desc": DESC_COTTON_RAW, "gst": 5.0},
        "raw cotton": {"hsn": "5201", "desc": DESC_COTTON_RAW, "gst": 5.0},
        "cotton lint": {"hsn": "5201", "desc": DESC_COTTON_RAW, "gst": 5.0},
        "cotton": {"hsn": "5201", "desc": DESC_COTTON_RAW, "gst": 5.0},
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
        
        # Agricultural - Oil Seeds
        "soybean": {"hsn": "1201", "desc": "Soya beans", "gst": 5.0},
        "soya": {"hsn": "1201", "desc": "Soya beans", "gst": 5.0},
        "sunflower": {"hsn": "1206", "desc": "Sunflower seeds", "gst": 5.0},
        "sunflower seed": {"hsn": "1206", "desc": "Sunflower seeds", "gst": 5.0},
        "groundnut": {"hsn": "1202", "desc": "Groundnuts (peanuts)", "gst": 5.0},
        "peanut": {"hsn": "1202", "desc": "Groundnuts (peanuts)", "gst": 5.0},
        
        # Synthetic fibers
        "polyester": {"hsn": "5503", "desc": "Synthetic staple fibers", "gst": 18.0},
        "viscose": {"hsn": "5504", "desc": "Artificial staple fibers", "gst": 18.0},
        
        # Precious Metals
        "gold": {"hsn": "7108", "desc": "Gold (including gold plated with platinum)", "gst": 3.0},
        "gold bar": {"hsn": "7108", "desc": "Gold in unwrought forms", "gst": 3.0},
        "gold coin": {"hsn": "7118", "desc": "Coin (other than legal tender)", "gst": 3.0},
        "silver": {"hsn": "7106", "desc": "Silver (including silver plated with gold)", "gst": 3.0},
        "silver bar": {"hsn": "7106", "desc": "Silver in unwrought forms", "gst": 3.0},
        "platinum": {"hsn": "7110", "desc": "Platinum, unwrought or in semi-manufactured forms", "gst": 3.0},
        
        # Base Metals
        "copper": {"hsn": "7402", "desc": "Copper, unrefined; copper anodes", "gst": 18.0},
        "copper wire": {"hsn": "7408", "desc": "Copper wire", "gst": 18.0},
        "aluminum": {"hsn": "7601", "desc": "Aluminium, unwrought", "gst": 18.0},
        "aluminium": {"hsn": "7601", "desc": "Aluminium, unwrought", "gst": 18.0},
        "steel": {"hsn": "7214", "desc": "Bars and rods of iron or steel", "gst": 18.0},
        "iron": {"hsn": "7203", "desc": "Ferrous products obtained by direct reduction", "gst": 18.0},
        
        # Edible Oils
        "palm oil": {"hsn": "1511", "desc": "Palm oil and its fractions", "gst": 5.0},
        "soybean oil": {"hsn": "1507", "desc": "Soya-bean oil and its fractions", "gst": 5.0},
        "sunflower oil": {"hsn": "1512", "desc": "Sunflower-seed oil", "gst": 5.0},
        "mustard oil": {"hsn": "1514", "desc": "Rape, colza or mustard oil", "gst": 5.0},
        "coconut oil": {"hsn": "1513", "desc": "Coconut (copra) oil", "gst": 5.0},
        "groundnut oil": {"hsn": "1508", "desc": "Groundnut oil and its fractions", "gst": 5.0},
        
        # Sugar & Sweeteners
        "sugar": {"hsn": "1701", "desc": "Cane or beet sugar", "gst": 5.0},
        "jaggery": {"hsn": "1701", "desc": "Cane or beet sugar (jaggery)", "gst": 5.0},
        "gur": {"hsn": "1701", "desc": "Cane or beet sugar (gur)", "gst": 5.0},
        
        # Spices
        "turmeric": {"hsn": "0910", "desc": "Ginger, saffron, turmeric", "gst": 5.0},
        "haldi": {"hsn": "0910", "desc": "Turmeric (curcuma)", "gst": 5.0},
        "black pepper": {"hsn": "0904", "desc": "Pepper of the genus Piper", "gst": 5.0},
        "pepper": {"hsn": "0904", "desc": "Pepper of the genus Piper", "gst": 5.0},
        "cardamom": {"hsn": "0908", "desc": "Cardamoms", "gst": 5.0},
        "elaichi": {"hsn": "0908", "desc": "Cardamoms", "gst": 5.0},
        "cumin": {"hsn": "0909", "desc": "Seeds of anise, badian, fennel, coriander, cumin", "gst": 5.0},
        "jeera": {"hsn": "0909", "desc": "Cumin seeds", "gst": 5.0},
        "coriander": {"hsn": "0909", "desc": "Coriander seeds", "gst": 5.0},
        "dhaniya": {"hsn": "0909", "desc": "Coriander seeds", "gst": 5.0},
        
        # Nuts & Dried Fruits
        "cashew": {"hsn": "0801", "desc": "Cashew nuts", "gst": 5.0},
        "almond": {"hsn": "0802", "desc": "Almonds", "gst": 5.0},
        "walnut": {"hsn": "0802", "desc": "Walnuts", "gst": 5.0},
        "pistachio": {"hsn": "0802", "desc": "Pistachios", "gst": 5.0},
        "raisin": {"hsn": "0806", "desc": "Grapes, dried (raisins)", "gst": 5.0},
        "dates": {"hsn": "0804", "desc": "Dates, figs, pineapples", "gst": 5.0},
        
        # Chemicals
        "urea": {"hsn": "3102", "desc": "Mineral or chemical fertilisers, nitrogenous", "gst": 5.0},
        "fertilizer": {"hsn": "3102", "desc": "Mineral or chemical fertilisers", "gst": 5.0},
        "pesticide": {"hsn": "3808", "desc": "Insecticides, rodenticides, fungicides", "gst": 18.0},
        
        # Plastics
        "plastic granules": {"hsn": "3901", "desc": "Polymers of ethylene, in primary forms", "gst": 18.0},
        "pvc": {"hsn": "3904", "desc": "Polymers of vinyl chloride", "gst": 18.0},
        "hdpe": {"hsn": "3901", "desc": "Polyethylene having a specific gravity of 0.94 or more", "gst": 18.0},
        "ldpe": {"hsn": "3901", "desc": "Polyethylene having a specific gravity of less than 0.94", "gst": 18.0},
        
        # Rubber
        "rubber": {"hsn": "4001", "desc": "Natural rubber", "gst": 18.0},
        "synthetic rubber": {"hsn": "4002", "desc": "Synthetic rubber", "gst": 18.0},
        
        # Paper & Pulp
        "paper": {"hsn": "4802", "desc": "Uncoated paper and paperboard", "gst": 12.0},
        "kraft paper": {"hsn": "4804", "desc": "Uncoated kraft paper", "gst": 12.0},
        "pulp": {"hsn": "4703", "desc": "Chemical wood pulp", "gst": 12.0},
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.hsn_api_enabled = os.getenv("HSN_API_ENABLED", "false").lower() == "true"
        self.hsn_api_key = os.getenv("HSN_API_KEY")
    
    async def suggest_hsn(
        self,
        commodity_name: str,
        category: Optional[str] = None,
        _description: Optional[str] = None  # Reserved for future use
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
        _category: Optional[str] = None  # Reserved for future filtering
    ) -> Optional[HSNSuggestion]:
        """Search learned HSN mappings"""
        
        # Return None if no database session
        if not self.db:
            return None
        
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
        _commodity_name: str,  # Reserved for future API integration
        _category: Optional[str]  # Reserved for future API integration
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
        
        # Function is async to maintain interface compatibility for future HTTP API calls
        # Satisfy linter by using asyncio.sleep(0) as a no-op async operation
        import asyncio
        await asyncio.sleep(0)
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
        
        # Skip if no database session
        if not self.db:
            return
        
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
        
        await self.db.flush()  # Flush instead of commit - let caller manage transaction

