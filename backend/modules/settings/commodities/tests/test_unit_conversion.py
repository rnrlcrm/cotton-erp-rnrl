"""
Unit Conversion System Tests

Comprehensive tests for unit catalog and unit converter functionality.
"""

import pytest
from decimal import Decimal

from backend.modules.settings.commodities.unit_catalog import (
    UNIT_CATALOG,
    get_unit_info,
    get_units_by_category,
    list_all_units,
    get_all_categories,
)
from backend.modules.settings.commodities.unit_converter import UnitConverter


class TestUnitCatalog:
    """Test unit catalog functionality"""
    
    def test_get_unit_info_valid_unit(self):
        """Test retrieving valid unit information"""
        candy_info = get_unit_info("CANDY")
        assert candy_info is not None
        assert candy_info["code"] == "CANDY"
        assert candy_info["name"] == "Candy"
        assert candy_info["category"] == "weight"
        assert candy_info["base_unit"] == "KG"
        assert candy_info["conversion_factor"] == Decimal("355.6222")
    
    def test_get_unit_info_exact_candy_conversion(self):
        """Test that CANDY uses exact 355.6222 KG conversion (not 356)"""
        candy_info = get_unit_info("CANDY")
        # CRITICAL: Must be 355.6222, not 356
        assert candy_info["conversion_factor"] == Decimal("355.6222")
        assert candy_info["conversion_factor"] != Decimal("356")
    
    def test_get_unit_info_invalid_unit(self):
        """Test retrieving invalid unit returns None"""
        invalid_unit = get_unit_info("INVALID_UNIT")
        assert invalid_unit is None
    
    def test_get_units_by_category_weight(self):
        """Test retrieving all weight units"""
        weight_units = get_units_by_category("weight")
        assert len(weight_units) > 0
        unit_codes = [u["code"] for u in weight_units]
        assert "KG" in unit_codes
        assert "CANDY" in unit_codes
        assert "QUINTAL" in unit_codes
        assert "MT" in unit_codes
    
    def test_get_units_by_category_count(self):
        """Test retrieving all count units"""
        count_units = get_units_by_category("count")
        assert len(count_units) > 0
        unit_codes = [u["code"] for u in count_units]
        assert "BALE" in unit_codes
        assert "BAG" in unit_codes
        assert "SACK" in unit_codes
    
    def test_get_units_by_category_invalid(self):
        """Test retrieving invalid category returns empty list"""
        invalid_units = get_units_by_category("invalid_category")
        assert invalid_units == []
    
    def test_list_all_units(self):
        """Test listing all units"""
        all_units = list_all_units()
        assert len(all_units) >= 36  # Should have 36+ units
        
        # Check some essential units are present
        assert "KG" in all_units
        assert "CANDY" in all_units
        assert "BALE" in all_units
        assert "METER" in all_units
        assert "LITER" in all_units
        assert "PIECE" in all_units
    
    def test_get_all_categories(self):
        """Test getting all categories"""
        categories = get_all_categories()
        assert "weight" in categories
        assert "count" in categories
        assert "length" in categories
        assert "volume" in categories
        assert "count_simple" in categories
        assert "area" in categories
    
    def test_catalog_structure(self):
        """Test that catalog has correct structure"""
        # Catalog is flat structure: {unit_code: unit_info}
        assert "KG" in UNIT_CATALOG
        assert "BALE" in UNIT_CATALOG
        
        # Test KG structure (base unit)
        kg = UNIT_CATALOG["KG"]
        assert kg["name"] == "Kilogram"
        assert kg["base_unit"] == "KG"
        assert kg["conversion_factor"] == Decimal("1.00")
        
        # Test BALE structure (count unit)
        bale = UNIT_CATALOG["BALE"]
        assert bale["name"] == "Bale (Cotton)"
        assert bale["base_unit"] == "KG"
        assert bale["conversion_factor"] == Decimal("170.00")


class TestUnitConverter:
    """Test unit converter functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.converter = UnitConverter()
    
    def test_convert_to_base_kg_to_kg(self):
        """Test converting KG to KG (identity)"""
        converter = UnitConverter()
        result = converter.convert_to_base(Decimal("100"), "KG", "KG")
        assert result == Decimal("100")
    
    def test_convert_to_base_bale_to_kg(self):
        """Test converting BALE to KG"""
        converter = UnitConverter()
        # 1 BALE = 170 KG
        result = converter.convert_to_base(Decimal("10"), "BALE", "KG")
        assert result == Decimal("1700")  # 10 × 170
    
    def test_convert_to_base_candy_to_kg(self):
        """Test converting CANDY to KG with exact precision"""
        converter = UnitConverter()
        # 1 CANDY = 355.6222 KG (exact)
        result = converter.convert_to_base(Decimal("1"), "CANDY", "KG")
        assert result == Decimal("355.6222")
    
    def test_convert_to_base_mt_to_kg(self):
        """Test converting MT to KG"""
        converter = UnitConverter()
        # 1 MT = 1000 KG
        result = converter.convert_to_base(Decimal("5"), "MT", "KG")
        assert result == Decimal("5000")
    
    def test_convert_from_base_kg_to_candy(self):
        """Test converting KG to CANDY"""
        converter = UnitConverter()
        # 355.6222 KG = 1 CANDY
        result = converter.convert_from_base(Decimal("355.6222"), "KG", "CANDY")
        assert result == Decimal("1")
    
    def test_convert_from_base_kg_to_quintal(self):
        """Test converting KG to QUINTAL"""
        converter = UnitConverter()
        # 100 KG = 1 QUINTAL
        result = converter.convert_from_base(Decimal("1000"), "KG", "QUINTAL")
        assert result == Decimal("10")
    
    def test_calculate_billing_amount_cotton_example(self):
        """
        Test Cotton example: 600 BALES @ ₹50,000/CANDY
        
        Calculation:
        - 600 BALES = 600 × 170 KG = 102,000 KG
        - ₹50,000/CANDY = ₹50,000/355.6222 KG = ₹140.61/KG
        - Billing = 102,000 × 140.61 = ₹14,341,200
        
        Formula: 600 × 170 × 0.002812 × 50,000 = ₹14,341,200
        """
        converter = UnitConverter()
        result = converter.calculate_billing_amount(
            trade_quantity=Decimal("600"),
            trade_unit="BALE",
            rate_per_unit=Decimal("50000"),
            rate_unit="CANDY",
            base_unit="KG"
        )
        
        assert result["quantity_in_base_unit"] == Decimal("102000")
        assert result["base_unit"] == "KG"
        
        # Rate per base unit: 50000 / 355.6222 ≈ 140.598
        rate_per_kg = result["rate_per_base_unit"]
        assert abs(rate_per_kg - Decimal("140.598")) < Decimal("0.01")
        
        # Billing amount: 102000 × 140.598... ≈ 14,341,059
        # Exact: 600 × 170 ÷ 355.6222 × 50000 = 14,341,059.32
        billing = result["billing_amount"]
        expected = Decimal("14341059")
        assert abs(billing - expected) < Decimal("100")
        
        # Check conversion factors
        assert "1 BALE = 170.00 KG" in result["conversion_factors"]["trade_unit_to_base"]
        assert "1 CANDY = 355.6222 KG" in result["conversion_factors"]["rate_unit_to_base"]
        
        # Check formula
        assert "600" in result["formula"]
        assert "BALE" in result["formula"]
        assert "170" in result["formula"]
        assert "CANDY" in result["formula"]
        assert "50,000" in result["formula"] or "50000" in result["formula"]
    
    def test_calculate_billing_amount_chana_example(self):
        """
        Test Chana example: 20 MT @ ₹2,500/QTL
        
        Calculation:
        - 20 MT = 20,000 KG
        - ₹2,500/QTL = ₹2,500/100 KG = ₹25/KG
        - Billing = 20,000 × 25 = ₹5,00,000
        """
        converter = UnitConverter()
        result = converter.calculate_billing_amount(
            trade_quantity=Decimal("20"),
            trade_unit="MT",
            rate_per_unit=Decimal("2500"),
            rate_unit="QUINTAL",
            base_unit="KG"
        )
        
        assert result["quantity_in_base_unit"] == Decimal("20000")
        assert result["base_unit"] == "KG"
        assert result["rate_per_base_unit"] == Decimal("25")
        assert result["billing_amount"] == Decimal("500000")
    
    def test_calculate_billing_amount_same_units(self):
        """Test when trade_unit and rate_unit are the same"""
        converter = UnitConverter()
        result = converter.calculate_billing_amount(
            trade_quantity=Decimal("100"),
            trade_unit="KG",
            rate_per_unit=Decimal("50"),
            rate_unit="KG",
            base_unit="KG"
        )
        
        assert result["quantity_in_base_unit"] == Decimal("100")
        assert result["rate_per_base_unit"] == Decimal("50")
        assert result["billing_amount"] == Decimal("5000")  # 100 × 50
    
    def test_validate_units_compatibility_valid(self):
        """Test validating compatible units"""
        converter = UnitConverter()
        # All weight units should be compatible
        assert converter.validate_units_compatibility("BALE", "CANDY", "KG") == True
        assert converter.validate_units_compatibility("MT", "QUINTAL", "KG") == True
    
    def test_validate_units_compatibility_invalid(self):
        """Test validating incompatible units"""
        converter = UnitConverter()
        # Weight and length units are incompatible
        with pytest.raises(ValueError, match="incompatible"):
            converter.validate_units_compatibility("BALE", "METER", "KG")
    
    def test_convert_to_base_invalid_unit(self):
        """Test converting with invalid unit raises error"""
        converter = UnitConverter()
        with pytest.raises(ValueError, match="Unknown unit"):
            converter.convert_to_base(Decimal("100"), "INVALID_UNIT", "KG")
    
    def test_convert_to_base_negative_quantity(self):
        """Test converting negative quantity raises error"""
        converter = UnitConverter()
        with pytest.raises(ValueError, match="Quantity must be positive"):
            converter.convert_to_base(Decimal("-10"), "KG", "KG")
    
    def test_convert_to_base_zero_quantity(self):
        """Test converting zero quantity raises error"""
        converter = UnitConverter()
        with pytest.raises(ValueError, match="Quantity must be positive"):
            converter.convert_to_base(Decimal("0"), "KG", "KG")
    
    def test_length_unit_conversion(self):
        """Test length unit conversion (METER base)"""
        converter = UnitConverter()
        # 5 KM = 5000 METER
        result = converter.convert_to_base(Decimal("5"), "KM", "METER")
        assert result == Decimal("5000")
        
        # 100 CM = 1 METER
        result = converter.convert_to_base(Decimal("100"), "CM", "METER")
        assert result == Decimal("1")
    
    def test_volume_unit_conversion(self):
        """Test volume unit conversion (LITER base)"""
        converter = UnitConverter()
        # 5 LITER = 5 LITER
        result = converter.convert_to_base(Decimal("5"), "LITER", "LITER")
        assert result == Decimal("5")
        
        # 2000 ML = 2 LITER
        result = converter.convert_to_base(Decimal("2000"), "ML", "LITER")
        assert result == Decimal("2")
    
    def test_count_simple_unit_conversion(self):
        """Test count simple unit conversion (PIECE base)"""
        converter = UnitConverter()
        # 2 DOZEN = 24 PIECE
        result = converter.convert_to_base(Decimal("2"), "DOZEN", "PIECE")
        assert result == Decimal("24")
        
        # 1 GROSS = 144 PIECE
        result = converter.convert_to_base(Decimal("1"), "GROSS", "PIECE")
        assert result == Decimal("144")
    
    def test_area_unit_conversion(self):
        """Test area unit conversion (SQ_METER base)"""
        converter = UnitConverter()
        # 100 SQ_METER = 100 SQ_METER
        result = converter.convert_to_base(Decimal("100"), "SQ_METER", "SQ_METER")
        assert result == Decimal("100")


class TestUnitConversionEdgeCases:
    """Test edge cases and error handling"""
    
    def test_precision_candy_conversion(self):
        """
        Test that CANDY conversion maintains precision.
        
        User specified EXACT 355.6222 KG, not 356 KG.
        The factor 0.002812 must be exact.
        """
        converter = UnitConverter()
        
        # 1 CANDY = 355.6222 KG (exact)
        kg_per_candy = converter.convert_to_base(Decimal("1"), "CANDY", "KG")
        assert kg_per_candy == Decimal("355.6222")
        
        # Reverse: 355.6222 KG = 1 CANDY (exact)
        candies = converter.convert_from_base(Decimal("355.6222"), "KG", "CANDY")
        assert candies == Decimal("1")
        
        # Factor check: 1 / 355.6222 ≈ 0.002812
        factor = Decimal("1") / Decimal("355.6222")
        expected_factor = Decimal("0.002812")
        # Allow small floating point difference
        assert abs(factor - expected_factor) < Decimal("0.000001")
    
    def test_large_quantities(self):
        """Test conversion with large quantities"""
        converter = UnitConverter()
        
        # 10,000 BALES to KG
        result = converter.convert_to_base(Decimal("10000"), "BALE", "KG")
        assert result == Decimal("1700000")  # 10,000 × 170
    
    def test_fractional_quantities(self):
        """Test conversion with fractional quantities"""
        converter = UnitConverter()
        
        # 0.5 BALE = 85 KG
        result = converter.convert_to_base(Decimal("0.5"), "BALE", "KG")
        assert result == Decimal("85")
    
    def test_incompatible_base_units_in_calculation(self):
        """Test billing calculation with incompatible base units"""
        converter = UnitConverter()
        
        # BALE (weight, KG base) vs METER (length) should fail
        with pytest.raises(ValueError, match="incompatible"):
            converter.calculate_billing_amount(
                trade_quantity=Decimal("100"),
                trade_unit="BALE",
                rate_per_unit=Decimal("50"),
                rate_unit="METER",
                base_unit="KG"
            )
    
    def test_missing_unit_in_catalog(self):
        """Test handling of units not in catalog"""
        converter = UnitConverter()
        
        with pytest.raises(ValueError, match="Unknown unit: NONEXISTENT"):
            converter.convert_to_base(Decimal("100"), "NONEXISTENT", "KG")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
