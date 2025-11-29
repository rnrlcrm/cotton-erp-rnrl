"""
Universal Unit Catalog for All Commodities

CRITICAL: CANDY conversion = 355.6222 KG (EXACT: 784 pounds, factor 0.002812)
All conversions are pre-defined. NO manual entry needed!

Multi-base support: KG, METER, LITER, PIECE, SQ_METER
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional


# Flat catalog structure: {unit_code: {metadata}}
UNIT_CATALOG: Dict[str, Dict[str, Any]] = {
    
    # ==================== WEIGHT UNITS (base: KG) ====================
    
    "KG": {
        "code": "KG",
        "name": "Kilogram",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("1.00"),
        "description": "Kilogram (base weight unit)"
    },
    
    "GRAM": {
        "code": "GRAM",
        "name": "Gram",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("0.001"),
        "description": "Gram (1/1000 KG)"
    },
    
    "QUINTAL": {
        "code": "QUINTAL",
        "name": "Quintal",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("100.00"),
        "description": "Quintal (100 KG)"
    },
    
    "QTL": {
        "code": "QTL",
        "name": "Quintal (QTL)",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("100.00"),
        "description": "Quintal abbreviation"
    },
    
    "MT": {
        "code": "MT",
        "name": "Metric Ton",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("1000.00"),
        "description": "Metric Ton (1000 KG)"
    },
    
    "TON": {
        "code": "TON",
        "name": "Ton",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("1000.00"),
        "description": "Metric Ton alias"
    },
    
    # COTTON-SPECIFIC (EXACT!)
    "CANDY": {
        "code": "CANDY",
        "name": "Candy",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("355.6222"),  # EXACT: 784 pounds
        "description": "Candy (784 pounds = 355.6222 KG) - Cotton unit"
    },
    
    "MAUND": {
        "code": "MAUND",
        "name": "Maund",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("37.324"),
        "description": "Maund (37.324 KG)"
    },
    
    # INTERNATIONAL WEIGHT
    "POUND": {
        "code": "POUND",
        "name": "Pound",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("0.453592"),
        "description": "Pound (lb)"
    },
    
    "LB": {
        "code": "LB",
        "name": "Pound (lb)",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("0.453592"),
        "description": "Pound abbreviation"
    },
    
    "OUNCE": {
        "code": "OUNCE",
        "name": "Ounce",
        "category": "weight",
        "base_unit": "KG",
        "conversion_factor": Decimal("0.0283495"),
        "description": "Ounce (oz)"
    },
    
    # ==================== COUNT UNITS (Packaging - base: KG) ====================
    
    "BALE": {
        "code": "BALE",
        "name": "Bale (Cotton)",
        "category": "count",
        "base_unit": "KG",
        "conversion_factor": Decimal("170.00"),  # Standard cotton bale
        "description": "Bale - standard 170 KG (customizable per commodity)"
    },
    
    "BAG": {
        "code": "BAG",
        "name": "Bag",
        "category": "count",
        "base_unit": "KG",
        "conversion_factor": Decimal("50.00"),  # Common bag weight
        "description": "Bag - standard 50 KG (customizable per commodity)"
    },
    
    "BAG_JUTE": {
        "code": "BAG_JUTE",
        "name": "Jute Bag",
        "category": "count",
        "base_unit": "KG",
        "conversion_factor": Decimal("100.00"),
        "description": "Jute Bag (100 KG)"
    },
    
    "SACK": {
        "code": "SACK",
        "name": "Sack",
        "category": "count",
        "base_unit": "KG",
        "conversion_factor": Decimal("50.00"),
        "description": "Sack (50 KG)"
    },
    
    "BOX": {
        "code": "BOX",
        "name": "Box",
        "category": "count",
        "base_unit": "KG",
        "conversion_factor": Decimal("10.00"),
        "description": "Box (10 KG default)"
    },
    
    "CARTON": {
        "code": "CARTON",
        "name": "Carton",
        "category": "count",
        "base_unit": "KG",
        "conversion_factor": Decimal("20.00"),
        "description": "Carton (20 KG default)"
    },
    
    "DRUM": {
        "code": "DRUM",
        "name": "Drum",
        "category": "count",
        "base_unit": "KG",
        "conversion_factor": Decimal("200.00"),
        "description": "Drum (200 KG default)"
    },
    
    # ==================== LENGTH UNITS (base: METER) ====================
    
    "METER": {
        "code": "METER",
        "name": "Meter",
        "category": "length",
        "base_unit": "METER",
        "conversion_factor": Decimal("1.00"),
        "description": "Meter (base length unit)"
    },
    
    "CM": {
        "code": "CM",
        "name": "Centimeter",
        "category": "length",
        "base_unit": "METER",
        "conversion_factor": Decimal("0.01"),
        "description": "Centimeter (1/100 meter)"
    },
    
    "KM": {
        "code": "KM",
        "name": "Kilometer",
        "category": "length",
        "base_unit": "METER",
        "conversion_factor": Decimal("1000.00"),
        "description": "Kilometer (1000 meters)"
    },
    
    "YARD": {
        "code": "YARD",
        "name": "Yard",
        "category": "length",
        "base_unit": "METER",
        "conversion_factor": Decimal("0.9144"),
        "description": "Yard"
    },
    
    "FOOT": {
        "code": "FOOT",
        "name": "Foot",
        "category": "length",
        "base_unit": "METER",
        "conversion_factor": Decimal("0.3048"),
        "description": "Foot (ft)"
    },
    
    "INCH": {
        "code": "INCH",
        "name": "Inch",
        "category": "length",
        "base_unit": "METER",
        "conversion_factor": Decimal("0.0254"),
        "description": "Inch (in)"
    },
    
    # ==================== VOLUME UNITS (base: LITER) ====================
    
    "LITER": {
        "code": "LITER",
        "name": "Liter",
        "category": "volume",
        "base_unit": "LITER",
        "conversion_factor": Decimal("1.00"),
        "description": "Liter (base volume unit)"
    },
    
    "ML": {
        "code": "ML",
        "name": "Milliliter",
        "category": "volume",
        "base_unit": "LITER",
        "conversion_factor": Decimal("0.001"),
        "description": "Milliliter (1/1000 liter)"
    },
    
    "GALLON": {
        "code": "GALLON",
        "name": "Gallon",
        "category": "volume",
        "base_unit": "LITER",
        "conversion_factor": Decimal("3.78541"),
        "description": "Gallon (US)"
    },
    
    "BARREL": {
        "code": "BARREL",
        "name": "Barrel",
        "category": "volume",
        "base_unit": "LITER",
        "conversion_factor": Decimal("159.00"),
        "description": "Barrel (oil, 159 liters)"
    },
    
    # ==================== COUNT SIMPLE (base: PIECE) ====================
    
    "PIECE": {
        "code": "PIECE",
        "name": "Piece",
        "category": "count_simple",
        "base_unit": "PIECE",
        "conversion_factor": Decimal("1.00"),
        "description": "Piece (base count unit)"
    },
    
    "PCS": {
        "code": "PCS",
        "name": "Pieces",
        "category": "count_simple",
        "base_unit": "PIECE",
        "conversion_factor": Decimal("1.00"),
        "description": "Pieces abbreviation"
    },
    
    "DOZEN": {
        "code": "DOZEN",
        "name": "Dozen",
        "category": "count_simple",
        "base_unit": "PIECE",
        "conversion_factor": Decimal("12.00"),
        "description": "Dozen (12 pieces)"
    },
    
    "GROSS": {
        "code": "GROSS",
        "name": "Gross",
        "category": "count_simple",
        "base_unit": "PIECE",
        "conversion_factor": Decimal("144.00"),
        "description": "Gross (144 pieces)"
    },
    
    "BUNDLE": {
        "code": "BUNDLE",
        "name": "Bundle",
        "category": "count_simple",
        "base_unit": "PIECE",
        "conversion_factor": Decimal("10.00"),
        "description": "Bundle (10 pieces default)"
    },
    
    # ==================== AREA UNITS (base: SQ_METER) ====================
    
    "SQ_METER": {
        "code": "SQ_METER",
        "name": "Square Meter",
        "category": "area",
        "base_unit": "SQ_METER",
        "conversion_factor": Decimal("1.00"),
        "description": "Square meter (base area unit)"
    },
    
    "SQ_FOOT": {
        "code": "SQ_FOOT",
        "name": "Square Foot",
        "category": "area",
        "base_unit": "SQ_METER",
        "conversion_factor": Decimal("0.092903"),
        "description": "Square foot"
    },
    
    "SQ_YARD": {
        "code": "SQ_YARD",
        "name": "Square Yard",
        "category": "area",
        "base_unit": "SQ_METER",
        "conversion_factor": Decimal("0.836127"),
        "description": "Square yard"
    },
}


# ==================== HELPER FUNCTIONS ====================

def get_unit_info(unit: str) -> Optional[Dict[str, Any]]:
    """
    Get complete unit information from catalog.
    
    Args:
        unit: Unit code (case-insensitive)
    
    Returns:
        Unit info dict or None if not found
    
    Example:
        >>> get_unit_info("CANDY")
        {
            "code": "CANDY",
            "name": "Candy",
            "category": "weight",
            "base_unit": "KG",
            "conversion_factor": Decimal("355.6222"),
            "description": "..."
        }
    """
    unit_upper = unit.upper().strip()
    return UNIT_CATALOG.get(unit_upper)


def get_units_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Get all units in a specific category.
    
    Args:
        category: Category name (weight, count, length, volume, count_simple, area)
    
    Returns:
        List of unit info dicts in that category
    
    Example:
        >>> units = get_units_by_category("weight")
        >>> len(units) > 0
        True
    """
    return [
        unit_info
        for unit_info in UNIT_CATALOG.values()
        if unit_info["category"] == category
    ]


def list_all_units() -> List[str]:
    """
    List all available unit codes.
    
    Returns:
        Sorted list of all unit codes
    
    Example:
        >>> units = list_all_units()
        >>> "KG" in units and "CANDY" in units
        True
    """
    return sorted(UNIT_CATALOG.keys())


def get_all_categories() -> List[str]:
    """
    Get all unique category names.
    
    Returns:
        Sorted list of category names
    
    Example:
        >>> categories = get_all_categories()
        >>> "weight" in categories and "count" in categories
        True
    """
    categories = set()
    for unit_info in UNIT_CATALOG.values():
        categories.add(unit_info["category"])
    return sorted(categories)
