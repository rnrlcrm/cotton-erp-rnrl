"""
Commodity AI Helpers

AI-powered intelligence for commodity management.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.settings.commodities.schemas import (
    CategorySuggestion,
    HSNSuggestion,
    ParameterSuggestion,
)
from backend.modules.settings.commodities.hsn_learning import HSNLearningService


class CommodityAIHelper:
    """AI helper for commodity operations with learning capabilities"""
    
    # Constants for duplicate strings
    DESC_COTTON_RAW = "Cotton, not carded or combed"
    CATEGORY_NATURAL_FIBER = "Natural Fiber"
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize AI helper.
        
        Args:
            db: Database session for learning service (optional for backwards compat)
        """
        self.db = db
        self.hsn_learning = HSNLearningService(db) if db else None
    
    # HSN Code database (Multi-commodity support)
    HSN_DATABASE = {
        # Cotton & Textiles
        "raw cotton": {"hsn": "5201", "desc": DESC_COTTON_RAW, "gst": 5.0},
        "cotton lint": {"hsn": "5201", "desc": DESC_COTTON_RAW, "gst": 5.0},
        "cotton waste": {"hsn": "5202", "desc": "Cotton waste", "gst": 5.0},
        "cotton yarn": {"hsn": "5205", "desc": "Cotton yarn containing >= 85% cotton", "gst": 5.0},
        "cotton fabric": {"hsn": "5208", "desc": "Woven fabrics of cotton", "gst": 5.0},
        "cotton seed": {"hsn": "1207", "desc": "Oil seeds and oleaginous fruits", "gst": 5.0},
        "polyester": {"hsn": "5503", "desc": "Synthetic staple fibers", "gst": 18.0},
        "viscose": {"hsn": "5504", "desc": "Artificial staple fibers", "gst": 18.0},
        
        # Grains
        "wheat": {"hsn": "1001", "desc": "Wheat and meslin", "gst": 5.0},
        "rice": {"hsn": "1006", "desc": "Rice", "gst": 5.0},
        "maize": {"hsn": "1005", "desc": "Maize (corn)", "gst": 5.0},
        
        # Precious Metals
        "gold": {"hsn": "7108", "desc": "Gold (including gold plated with platinum)", "gst": 3.0},
        "silver": {"hsn": "7106", "desc": "Silver (including silver plated with gold)", "gst": 3.0},
        
        # Edible Oils
        "palm oil": {"hsn": "1511", "desc": "Palm oil and its fractions", "gst": 5.0},
        "soybean oil": {"hsn": "1507", "desc": "Soya-bean oil and its fractions", "gst": 5.0},
        "sunflower oil": {"hsn": "1512", "desc": "Sunflower-seed oil", "gst": 5.0},
    }
    
    # Category detection patterns (Multi-commodity support)
    CATEGORY_PATTERNS = {
        "Natural Fiber": ["cotton", "jute", "silk", "wool", "linen"],
        "Synthetic Fiber": ["polyester", "nylon", "acrylic", "spandex"],
        "Blended Fiber": ["poly cotton", "cotton blend", "mixed fiber"],
        "Waste": ["waste", "scrap", "residue"],
        "Yarn": ["yarn", "thread", "spun"],
        "Fabric": ["fabric", "cloth", "textile"],
        "Seed": ["seed", "ginned"],
        "Grains": ["wheat", "rice", "maize", "corn", "barley", "oats"],
        "Precious Metals": ["gold", "silver", "platinum", "palladium"],
        "Base Metals": ["copper", "aluminum", "aluminium", "steel", "iron", "zinc", "lead"],
        "Edible Oils": ["oil", "palm oil", "soybean oil", "sunflower oil", "mustard oil", "coconut oil"],
        "Pulses": ["dal", "chana", "chickpea", "lentil", "moong", "tur", "urad"],
        "Spices": ["turmeric", "pepper", "cardamom", "cumin", "coriander", "chili"],
        "Sugar": ["sugar", "jaggery", "gur"],
    }
    
    # Standard parameters by category
    STANDARD_PARAMETERS = {
        "Natural Fiber - Cotton": [
            {
                "name": "Staple Length",
                "type": "NUMERIC",
                "unit": "mm",
                "typical_range": [Decimal("28"), Decimal("32")],
                "mandatory": True,
                "description": "Fiber length in millimeters"
            },
            {
                "name": "Micronaire",
                "type": "NUMERIC",
                "unit": "units",
                "typical_range": [Decimal("3.5"), Decimal("4.9")],
                "mandatory": True,
                "description": "Fiber fineness and maturity"
            },
            {
                "name": "Strength",
                "type": "NUMERIC",
                "unit": "g/tex",
                "typical_range": [Decimal("26"), Decimal("32")],
                "mandatory": True,
                "description": "Fiber strength"
            },
            {
                "name": "Color Grade",
                "type": "TEXT",
                "unit": None,
                "typical_range": None,
                "mandatory": False,
                "description": "Color classification (White, Spotted, Tinged)"
            },
            {
                "name": "Trash Content",
                "type": "NUMERIC",
                "unit": "%",
                "typical_range": [Decimal("0"), Decimal("5")],
                "mandatory": False,
                "description": "Percentage of foreign matter"
            },
        ],
        "Yarn": [
            {
                "name": "Count",
                "type": "TEXT",
                "unit": "Ne",
                "typical_range": None,
                "mandatory": True,
                "description": "Yarn count"
            },
            {
                "name": "Twist",
                "type": "NUMERIC",
                "unit": "TPI",
                "typical_range": [Decimal("10"), Decimal("30")],
                "mandatory": False,
                "description": "Turns per inch"
            },
            {
                "name": "Strength",
                "type": "NUMERIC",
                "unit": "cN/tex",
                "typical_range": [Decimal("10"), Decimal("20")],
                "mandatory": True,
                "description": "Yarn strength"
            },
        ],
        "Fabric": [
            {
                "name": "Width",
                "type": "NUMERIC",
                "unit": "inches",
                "typical_range": [Decimal("36"), Decimal("72")],
                "mandatory": True,
                "description": "Fabric width"
            },
            {
                "name": "GSM",
                "type": "NUMERIC",
                "unit": "g/m²",
                "typical_range": [Decimal("100"), Decimal("300")],
                "mandatory": True,
                "description": "Grams per square meter"
            },
            {
                "name": "Construction",
                "type": "TEXT",
                "unit": None,
                "typical_range": None,
                "mandatory": False,
                "description": "Weave construction"
            },
        ],
    }
    
    async def detect_commodity_category(
        self,
        name: str,
        description: Optional[str] = None
    ) -> CategorySuggestion:
        """
        Detect commodity category from name and description.
        
        Uses pattern matching to identify category.
        In production, this would use ML model.
        """
        # Function is async for future ML model integration
        import asyncio
        await asyncio.sleep(0)
        
        combined_text = f"{name} {description or ''}".lower()
        
        # Find matching category
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern in combined_text:
                    # Check for sub-category
                    subcategory = None
                    if "cotton" in combined_text:
                        subcategory = "Cotton"
                    elif "polyester" in combined_text:
                        subcategory = "Polyester"
                    
                    return CategorySuggestion(
                        category=category,
                        confidence=0.85,
                        subcategory=subcategory
                    )
        
        # Default fallback
        return CategorySuggestion(
            category=self.CATEGORY_NATURAL_FIBER,
            confidence=0.50,
            subcategory=None
        )
    
    async def suggest_hsn_code(
        self,
        name: str,
        category: str,
        description: Optional[str] = None
    ) -> HSNSuggestion:
        """
        Suggest HSN code based on commodity name and category.
        
        Uses intelligent learning system:
        1. Checks knowledge base (learned mappings)
        2. Queries HSN API (if configured)
        3. Falls back to local data
        """
        
        # Use learning service if available (new behavior)
        if self.hsn_learning:
            return await self.hsn_learning.suggest_hsn(name, category, description)
        
        # Fallback to old hardcoded logic (backwards compatibility)
        search_text = name.lower()
        
        # Try exact match first
        for keyword, hsn_data in self.HSN_DATABASE.items():
            if keyword in search_text:
                return HSNSuggestion(
                    hsn_code=hsn_data["hsn"],
                    description=hsn_data["desc"],
                    gst_rate=Decimal(str(hsn_data["gst"])),
                    confidence=0.90
                )
        
        # Category-based fallback
        if "cotton" in category.lower() or "natural" in category.lower():
            return HSNSuggestion(
                hsn_code="5201",
                description="Cotton, not carded or combed",
                gst_rate=Decimal("5.0"),
                confidence=0.60
            )
        elif "synthetic" in category.lower():
            return HSNSuggestion(
                hsn_code="5503",
                description="Synthetic staple fibers",
                gst_rate=Decimal("18.0"),
                confidence=0.60
            )
        
        # Generic fallback
        return HSNSuggestion(
            hsn_code="5201",
            description="Cotton and textile products",
            gst_rate=Decimal("5.0"),
            confidence=0.40
        )
    
    async def suggest_quality_parameters(
        self,
        _commodity_id: UUID,  # Reserved for future database template queries
        category: str,
        name: str
    ) -> List[ParameterSuggestion]:
        """
        Suggest quality parameters based on commodity category.
        
        Uses intelligent system:
        1. Queries database templates (if db available)
        2. Falls back to hardcoded standards
        """
        
        # Use database templates if available (new behavior)
        if self.db:
            from backend.modules.settings.commodities.models import SystemCommodityParameter
            from sqlalchemy import select
            
            # Search for templates matching this category
            # Order by usage_count DESC to show most popular parameters first (AI learning)
            stmt = select(SystemCommodityParameter).where(
                SystemCommodityParameter.commodity_category.ilike(f"%{category}%")
            ).order_by(
                SystemCommodityParameter.usage_count.desc(),
                SystemCommodityParameter.is_mandatory.desc(),
                SystemCommodityParameter.parameter_name
            ).limit(20)
            
            result = await self.db.execute(stmt)
            templates = result.scalars().all()
            
            if templates:
                suggestions = []
                for template in templates:
                    suggestions.append(
                        ParameterSuggestion(
                            name=template.parameter_name,
                            type=template.parameter_type,
                            unit=template.unit,
                            typical_range=f"{template.min_value}-{template.max_value}" if template.min_value else None,
                            mandatory=template.is_mandatory,
                            description=template.description or f"Standard {template.parameter_name} measurement"
                        )
                    )
                return suggestions
        
        # Fallback to hardcoded logic (backwards compatibility)
        # Determine specific category key
        category_key = category
        
        # Refine for specific sub-categories
        if "cotton" in name.lower() and self.CATEGORY_NATURAL_FIBER in category:
            category_key = f"{self.CATEGORY_NATURAL_FIBER} - Cotton"
        elif "yarn" in name.lower():
            category_key = "Yarn"
        elif "fabric" in name.lower() or "cloth" in name.lower():
            category_key = "Fabric"
        
        # Get standard parameters
        parameters = self.STANDARD_PARAMETERS.get(category_key, [])
        
        # Convert to ParameterSuggestion format
        suggestions = []
        for param in parameters:
            suggestions.append(
                ParameterSuggestion(
                    name=param["name"],
                    type=param["type"],
                    unit=param["unit"],
                    typical_range=param["typical_range"],
                    mandatory=param["mandatory"],
                    description=param["description"]
                )
            )
        
        return suggestions
    
    async def validate_commodity_data(
        self,
        data: Dict
    ) -> Dict[str, List[str]]:
        """
        Validate commodity data for anomalies.
        
        Returns dict of field -> list of warnings.
        """
        # Function is async for future database validation queries
        import asyncio
        await asyncio.sleep(0)
        
        warnings = {}
        
        # Validate HSN vs Category
        if data.get("hsn_code") and data.get("category"):
            hsn = data["hsn_code"]
            category = data["category"].lower()
            
            # Cotton should be 52xx
            if "cotton" in category and not hsn.startswith("52"):
                warnings.setdefault("hsn_code", []).append(
                    f"HSN code {hsn} seems unusual for cotton (expected 52xx)"
                )
            
            # Synthetic should be 55xx
            if "synthetic" in category and not hsn.startswith("55"):
                warnings.setdefault("hsn_code", []).append(
                    f"HSN code {hsn} seems unusual for synthetic fiber (expected 55xx)"
                )
        
        # Validate GST Rate
        if data.get("gst_rate"):
            gst = float(data["gst_rate"])
            valid_rates = [0, 5, 12, 18, 28]
            
            if gst not in valid_rates:
                warnings.setdefault("gst_rate", []).append(
                    f"GST rate {gst}% is unusual (valid rates: {valid_rates})"
                )
        
        # Validate parameter ranges
        if data.get("min_value") and data.get("max_value"):
            min_val = float(data["min_value"])
            max_val = float(data["max_value"])
            
            if min_val >= max_val:
                warnings.setdefault("range", []).append(
                    "Minimum value should be less than maximum value"
                )
        
        return warnings
    
    async def enrich_commodity_data(
        self,
        name: str,
        category: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict:
        """
        AI-powered data enrichment for commodity.
        
        Returns suggested category, HSN, and basic info.
        """
        # Detect category if not provided
        if not category:
            category_suggestion = await self.detect_commodity_category(name, description)
            category = category_suggestion.category
        
        # Suggest HSN code
        hsn_suggestion = await self.suggest_hsn_code(name, category, description)
        
        return {
            "suggested_category": category,
            "suggested_hsn_code": hsn_suggestion.hsn_code,
            "suggested_gst_rate": hsn_suggestion.gst_rate,
            "hsn_description": hsn_suggestion.description,
            "confidence": {
                "category": 0.85,
                "hsn": hsn_suggestion.confidence
            }
        }
    
    # ==================== INTERNATIONAL FIELD AUTO-POPULATION ====================
    
    # International commodity intelligence database
    INTERNATIONAL_COMMODITY_DATA = {
        "Cotton": {
            "default_currency": "USD",
            "supported_currencies": ["USD", "INR", "CNY", "EUR", "GBP"],
            "international_pricing_unit": "CENTS_PER_POUND",
            "hs_code_6digit": "520100",
            "country_tax_codes": {
                "IND": {"hsn": "5201", "gst": 5.0},
                "USA": {"hts": "520100", "duty": 0},
                "EU": {"taric": "5201000000", "vat": 21.0},
                "CHN": {"hs": "520100", "vat": 13.0}
            },
            "quality_standards": ["USDA", "BCI", "CCI", "ISO_3920"],
            "international_grades": {
                "USDA": ["Strict Low Middling", "Low Middling", "Strict Middling", "Middling", "Strict Good Middling"],
                "Liverpool": ["Good Fair", "Fair", "Good", "Fully Good", "Good Middling"],
                "Indian": ["F-FAQ", "FAQ", "S-FAQ", "GS-FAQ"]
            },
            "certification_required": {"organic": False, "bci": True, "fair_trade": False},
            "major_producing_countries": ["India", "China", "USA", "Brazil", "Pakistan"],
            "major_consuming_countries": ["China", "India", "Bangladesh", "Pakistan", "Turkey"],
            "trading_hubs": ["Mumbai", "New York", "Liverpool", "Shanghai", "Karachi"],
            "traded_on_exchanges": ["MCX", "ICE_Futures", "ZCE", "NCDEX"],
            "contract_specifications": {
                "MCX": {"lot_size": "25 bales", "bale_weight": "170 kg"},
                "ICE": {"lot_size": "50000 lbs", "grade": "Strict Low Middling"}
            },
            "price_volatility": "HIGH",
            "export_regulations": {"license_required": False, "restricted_countries": []},
            "import_regulations": {"license_required": False, "quota": False},
            "phytosanitary_required": True,
            "fumigation_required": True,
            "seasonal_commodity": True,
            "harvest_season": {
                "India": ["Oct", "Nov", "Dec", "Jan"],
                "USA": ["Aug", "Sep", "Oct"],
                "China": ["Sep", "Oct", "Nov"]
            },
            "shelf_life_days": 730,
            "storage_conditions": {"temperature": "15-25°C", "humidity": "<65%", "ventilation": "Good"},
            "standard_lot_size": {"domestic": {"value": 25, "unit": "BALES"}, "international": {"value": 100, "unit": "BALES"}},
            "min_order_quantity": {"value": 10, "unit": "BALES"},
            "delivery_tolerance_pct": 5.0,
            "weight_tolerance_pct": 2.0
        },
        "Wheat": {
            "default_currency": "USD",
            "supported_currencies": ["USD", "INR", "EUR", "RUB"],
            "international_pricing_unit": "USD_PER_MT",
            "hs_code_6digit": "100190",
            "country_tax_codes": {
                "IND": {"hsn": "1001", "gst": 0},
                "USA": {"hts": "100190", "duty": 0},
                "EU": {"taric": "1001909900", "vat": 0},
                "CHN": {"hs": "100190", "vat": 9.0}
            },
            "quality_standards": ["USDA", "ISO_7970", "Codex_Alimentarius"],
            "international_grades": {
                "USDA": ["US No. 1", "US No. 2", "US No. 3"],
                "Indian": ["Sharbati", "Lokwan", "Durum"]
            },
            "certification_required": {"organic": False, "food_safe": True},
            "major_producing_countries": ["China", "India", "Russia", "USA", "France"],
            "major_consuming_countries": ["China", "India", "EU", "Egypt", "Iran"],
            "trading_hubs": ["Chicago", "Kansas City", "Paris", "Mumbai"],
            "traded_on_exchanges": ["CBOT", "Euronext", "NCDEX", "DGCX"],
            "contract_specifications": {
                "CBOT": {"lot_size": "5000 bushels", "grade": "No. 2 Soft Red"},
                "NCDEX": {"lot_size": "10 MT", "variety": "PBW 343"}
            },
            "price_volatility": "MEDIUM",
            "export_regulations": {"license_required": True, "restricted_countries": []},
            "import_regulations": {"license_required": False, "quota": True},
            "phytosanitary_required": True,
            "fumigation_required": False,
            "seasonal_commodity": True,
            "harvest_season": {
                "India": ["Mar", "Apr"],
                "USA": ["Jun", "Jul"],
                "Russia": ["Jul", "Aug"]
            },
            "shelf_life_days": 365,
            "storage_conditions": {"temperature": "10-15°C", "humidity": "<14%", "pest_control": "Required"},
            "standard_lot_size": {"domestic": {"value": 10, "unit": "MT"}, "international": {"value": 50, "unit": "MT"}},
            "min_order_quantity": {"value": 5, "unit": "MT"},
            "delivery_tolerance_pct": 2.0,
            "weight_tolerance_pct": 1.0
        },
        "Gold": {
            "default_currency": "USD",
            "supported_currencies": ["USD", "INR", "EUR", "GBP", "CHF", "JPY"],
            "international_pricing_unit": "USD_PER_TROY_OUNCE",
            "hs_code_6digit": "710812",
            "country_tax_codes": {
                "IND": {"hsn": "7108", "gst": 3.0},
                "USA": {"hts": "710812", "duty": 0},
                "EU": {"taric": "7108120000", "vat": 0},
                "CHN": {"hs": "710812", "vat": 13.0}
            },
            "quality_standards": ["LBMA", "ISO_9001", "BIS_Hallmark"],
            "international_grades": {
                "Purity": ["24K", "22K", "18K", "14K"],
                "LBMA": ["Good Delivery Bar (400 oz)", "Kilo Bar"]
            },
            "certification_required": {"lbma_approved": True, "assay_certificate": True},
            "major_producing_countries": ["China", "Australia", "Russia", "USA", "Canada"],
            "major_consuming_countries": ["China", "India", "USA", "Turkey", "Saudi Arabia"],
            "trading_hubs": ["London", "New York", "Zurich", "Dubai", "Mumbai"],
            "traded_on_exchanges": ["COMEX", "LBMA", "MCX", "TOCOM", "SGE"],
            "contract_specifications": {
                "COMEX": {"lot_size": "100 troy oz", "purity": "0.995"},
                "MCX": {"lot_size": "1 kg", "purity": "0.995"}
            },
            "price_volatility": "MEDIUM",
            "export_regulations": {"license_required": True, "customs_declaration": True},
            "import_regulations": {"license_required": True, "quota": False, "duty": "Varies"},
            "phytosanitary_required": False,
            "fumigation_required": False,
            "seasonal_commodity": False,
            "harvest_season": {},
            "shelf_life_days": None,
            "storage_conditions": {"security": "High", "insurance": "Required", "vault_storage": True},
            "standard_lot_size": {"domestic": {"value": 1, "unit": "KG"}, "international": {"value": 400, "unit": "TROY_OZ"}},
            "min_order_quantity": {"value": 10, "unit": "GRAMS"},
            "delivery_tolerance_pct": 0.0,
            "weight_tolerance_pct": 0.1
        }
    }
    
    async def suggest_international_fields(self, commodity_name: str, category: Optional[str] = None) -> Dict:
        """
        AI-powered international field suggestions.
        
        Auto-populates 90% of international fields based on commodity intelligence.
        """
        # Normalize commodity name
        normalized_name = commodity_name.strip().lower()
        
        # Find matching template
        template_key = None
        for key in self.INTERNATIONAL_COMMODITY_DATA.keys():
            if key.lower() in normalized_name:
                template_key = key
                break
        
        if not template_key:
            # Default fallback for unknown commodities
            return self._get_default_international_fields(commodity_name, category)
        
        # Get template data
        template = self.INTERNATIONAL_COMMODITY_DATA[template_key].copy()
        
        return {
            "confidence": 0.95 if template_key else 0.5,
            "template_used": template_key,
            "international_fields": template
        }
    
    def _get_default_international_fields(self, commodity_name: str, category: Optional[str]) -> Dict:
        """Default international fields for unknown commodities"""
        return {
            "confidence": 0.4,
            "template_used": "DEFAULT",
            "international_fields": {
                "default_currency": "USD",
                "supported_currencies": ["USD", "INR", "EUR"],
                "international_pricing_unit": "USD_PER_KG",
                "hs_code_6digit": None,
                "country_tax_codes": {},
                "quality_standards": [],
                "international_grades": {},
                "certification_required": {},
                "major_producing_countries": [],
                "major_consuming_countries": [],
                "trading_hubs": [],
                "traded_on_exchanges": [],
                "contract_specifications": {},
                "price_volatility": "MEDIUM",
                "export_regulations": {"license_required": False},
                "import_regulations": {"license_required": False},
                "phytosanitary_required": False,
                "fumigation_required": False,
                "seasonal_commodity": False,
                "harvest_season": {},
                "shelf_life_days": None,
                "storage_conditions": {},
                "standard_lot_size": {"domestic": {"value": 1, "unit": "MT"}},
                "min_order_quantity": {"value": 1, "unit": "MT"},
                "delivery_tolerance_pct": 5.0,
                "weight_tolerance_pct": 2.0
            }
        }
