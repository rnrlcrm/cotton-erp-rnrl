"""
Seed Data: SystemCommodityParameter Templates

Pre-populate quality parameter templates for major commodity categories.
These serve as AI suggestions for new commodities.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from backend.db.session import SessionLocal
from backend.modules.settings.commodities.models import SystemCommodityParameter


# Template definitions for major commodity categories
PARAMETER_TEMPLATES = [
    # ==================== COTTON ====================
    {
        "commodity_category": "Cotton",
        "parameter_name": "Staple Length",
        "parameter_type": "RANGE",
        "unit": "mm",
        "min_value": Decimal("22.0"),
        "max_value": Decimal("34.0"),
        "is_mandatory": True,
        "description": "Fiber length measurement, critical for yarn quality",
        "source": "SEED",
        "usage_count": 10,
    },
    {
        "commodity_category": "Cotton",
        "parameter_name": "Micronaire",
        "parameter_type": "RANGE",
        "unit": "μg/inch",
        "min_value": Decimal("2.5"),
        "max_value": Decimal("6.0"),
        "is_mandatory": True,
        "description": "Fiber fineness and maturity measurement",
        "source": "SEED",
        "usage_count": 10,
    },
    {
        "commodity_category": "Cotton",
        "parameter_name": "Strength",
        "parameter_type": "RANGE",
        "unit": "g/tex",
        "min_value": Decimal("22.0"),
        "max_value": Decimal("35.0"),
        "is_mandatory": True,
        "description": "Fiber tensile strength",
        "source": "SEED",
        "usage_count": 10,
    },
    {
        "commodity_category": "Cotton",
        "parameter_name": "Color Grade",
        "parameter_type": "TEXT",
        "unit": None,
        "min_value": None,
        "max_value": None,
        "is_mandatory": True,
        "description": "Visual appearance classification (e.g., White, Spotted, Tinged)",
        "source": "SEED",
        "usage_count": 10,
    },
    {
        "commodity_category": "Cotton",
        "parameter_name": "Trash Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.0"),
        "max_value": Decimal("5.0"),
        "is_mandatory": True,
        "description": "Foreign matter percentage",
        "source": "SEED",
        "usage_count": 9,
    },
    {
        "commodity_category": "Cotton",
        "parameter_name": "Moisture Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("6.0"),
        "max_value": Decimal("8.5"),
        "is_mandatory": True,
        "description": "Water content percentage",
        "source": "SEED",
        "usage_count": 9,
    },
    
    # ==================== PULSES ====================
    {
        "commodity_category": "Pulses",
        "parameter_name": "Moisture Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("10.0"),
        "max_value": Decimal("12.0"),
        "is_mandatory": True,
        "description": "Water content for storage stability",
        "source": "SEED",
        "usage_count": 15,
    },
    {
        "commodity_category": "Pulses",
        "parameter_name": "Foreign Matter",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.0"),
        "max_value": Decimal("1.0"),
        "is_mandatory": True,
        "description": "Impurities and foreign material",
        "source": "SEED",
        "usage_count": 15,
    },
    {
        "commodity_category": "Pulses",
        "parameter_name": "Damaged Grains",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.0"),
        "max_value": Decimal("3.0"),
        "is_mandatory": True,
        "description": "Percentage of broken or damaged grains",
        "source": "SEED",
        "usage_count": 12,
    },
    {
        "commodity_category": "Pulses",
        "parameter_name": "Protein Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("18.0"),
        "max_value": Decimal("25.0"),
        "is_mandatory": False,
        "description": "Nutritional protein percentage",
        "source": "SEED",
        "usage_count": 8,
    },
    {
        "commodity_category": "Pulses",
        "parameter_name": "Weevilled Grains",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.0"),
        "max_value": Decimal("1.0"),
        "is_mandatory": True,
        "description": "Insect-damaged grains",
        "source": "SEED",
        "usage_count": 10,
    },
    
    # ==================== GRAINS (Wheat, Rice, etc.) ====================
    {
        "commodity_category": "Grains",
        "parameter_name": "Moisture Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("12.0"),
        "max_value": Decimal("14.0"),
        "is_mandatory": True,
        "description": "Water content for safe storage",
        "source": "SEED",
        "usage_count": 20,
    },
    {
        "commodity_category": "Grains",
        "parameter_name": "Foreign Matter",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.0"),
        "max_value": Decimal("2.0"),
        "is_mandatory": True,
        "description": "Non-grain materials and impurities",
        "source": "SEED",
        "usage_count": 20,
    },
    {
        "commodity_category": "Grains",
        "parameter_name": "Broken Grains",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.0"),
        "max_value": Decimal("5.0"),
        "is_mandatory": True,
        "description": "Percentage of broken or shriveled grains",
        "source": "SEED",
        "usage_count": 18,
    },
    {
        "commodity_category": "Grains",
        "parameter_name": "Test Weight",
        "parameter_type": "RANGE",
        "unit": "kg/hl",
        "min_value": Decimal("72.0"),
        "max_value": Decimal("82.0"),
        "is_mandatory": False,
        "description": "Hectoliter weight (grain density)",
        "source": "SEED",
        "usage_count": 12,
    },
    {
        "commodity_category": "Grains",
        "parameter_name": "Protein Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("10.0"),
        "max_value": Decimal("14.0"),
        "is_mandatory": False,
        "description": "Protein percentage (wheat quality indicator)",
        "source": "SEED",
        "usage_count": 10,
    },
    
    # ==================== OIL SEEDS ====================
    {
        "commodity_category": "Oil Seeds",
        "parameter_name": "Oil Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("35.0"),
        "max_value": Decimal("45.0"),
        "is_mandatory": True,
        "description": "Extractable oil percentage",
        "source": "SEED",
        "usage_count": 15,
    },
    {
        "commodity_category": "Oil Seeds",
        "parameter_name": "Moisture Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("6.0"),
        "max_value": Decimal("9.0"),
        "is_mandatory": True,
        "description": "Water content for storage",
        "source": "SEED",
        "usage_count": 15,
    },
    {
        "commodity_category": "Oil Seeds",
        "parameter_name": "Foreign Matter",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.0"),
        "max_value": Decimal("2.0"),
        "is_mandatory": True,
        "description": "Non-seed impurities",
        "source": "SEED",
        "usage_count": 14,
    },
    {
        "commodity_category": "Oil Seeds",
        "parameter_name": "Damaged Seeds",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.0"),
        "max_value": Decimal("3.0"),
        "is_mandatory": True,
        "description": "Broken or damaged seeds",
        "source": "SEED",
        "usage_count": 12,
    },
    {
        "commodity_category": "Oil Seeds",
        "parameter_name": "Free Fatty Acid",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("0.5"),
        "max_value": Decimal("2.0"),
        "is_mandatory": False,
        "description": "FFA content (quality indicator)",
        "source": "SEED",
        "usage_count": 8,
    },
    
    # ==================== YARN ====================
    {
        "commodity_category": "Yarn",
        "parameter_name": "Count",
        "parameter_type": "TEXT",
        "unit": "Ne",
        "min_value": None,
        "max_value": None,
        "is_mandatory": True,
        "description": "Yarn count/fineness (e.g., 20s, 30s, 40s)",
        "source": "SEED",
        "usage_count": 12,
    },
    {
        "commodity_category": "Yarn",
        "parameter_name": "Ply",
        "parameter_type": "NUMERIC",
        "unit": None,
        "min_value": Decimal("1.0"),
        "max_value": Decimal("6.0"),
        "is_mandatory": True,
        "description": "Number of strands twisted together",
        "source": "SEED",
        "usage_count": 12,
    },
    {
        "commodity_category": "Yarn",
        "parameter_name": "Twist Per Inch",
        "parameter_type": "RANGE",
        "unit": "TPI",
        "min_value": Decimal("10.0"),
        "max_value": Decimal("30.0"),
        "is_mandatory": False,
        "description": "Number of twists per inch",
        "source": "SEED",
        "usage_count": 10,
    },
    {
        "commodity_category": "Yarn",
        "parameter_name": "Strength",
        "parameter_type": "RANGE",
        "unit": "cN/tex",
        "min_value": Decimal("12.0"),
        "max_value": Decimal("18.0"),
        "is_mandatory": False,
        "description": "Yarn tensile strength",
        "source": "SEED",
        "usage_count": 9,
    },
    {
        "commodity_category": "Yarn",
        "parameter_name": "Moisture Content",
        "parameter_type": "RANGE",
        "unit": "%",
        "min_value": Decimal("6.5"),
        "max_value": Decimal("8.5"),
        "is_mandatory": True,
        "description": "Moisture regain percentage",
        "source": "SEED",
        "usage_count": 11,
    },
]


def seed_parameter_templates() -> None:
    """Seed SystemCommodityParameter templates into database"""
    
    db = SessionLocal()
    
    try:
        print("🌱 Seeding commodity parameter templates...")
        
        created_count = 0
        skipped_count = 0
        
        for template_data in PARAMETER_TEMPLATES:
            # Check if template already exists
            stmt = select(SystemCommodityParameter).where(
                SystemCommodityParameter.commodity_category == template_data["commodity_category"],
                SystemCommodityParameter.parameter_name == template_data["parameter_name"]
            )
            result = db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                skipped_count += 1
                print(f"  ⏭️  Skipped: {template_data['commodity_category']} - {template_data['parameter_name']} (already exists)")
                continue
            
            # Create new template
            template = SystemCommodityParameter(**template_data)
            db.add(template)
            created_count += 1
            print(f"  ✅ Created: {template_data['commodity_category']} - {template_data['parameter_name']}")
        
        db.commit()
        
        print(f"\n✅ Seeding complete!")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total templates: {len(PARAMETER_TEMPLATES)}")
    
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding templates: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_parameter_templates()
