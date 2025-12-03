"""
Unit Tests for International Commodity Features

Comprehensive test suite covering:
- International field validation
- AI suggestion templates
- Multi-currency pricing
- Schema validation
- Edge cases
"""

import pytest
from decimal import Decimal
from typing import Dict
from pydantic import ValidationError

from backend.modules.settings.commodities.schemas import (
    CommodityCreate,
    CommodityUpdate,
    InternationalFieldsSuggestion
)
from backend.modules.settings.commodities.ai_helpers import CommodityAIHelper
from backend.modules.settings.commodities.pricing_service import CommodityPricingService


class TestInternationalFieldValidation:
    """Test international field validation in schemas"""
    
    def test_commodity_create_with_international_fields(self):
        """Test creating commodity with all international fields"""
        data = CommodityCreate(
            name="Cotton - Raw",
            category="Natural Fiber",
            hsn_code="5201",
            gst_rate=Decimal("5.0"),
            default_currency="USD",
            supported_currencies=["USD", "INR", "EUR"],
            international_pricing_unit="CENTS_PER_POUND",
            hs_code_6digit="520100",
            country_tax_codes={
                "IND": {"hsn": "5201", "gst": 5.0},
                "USA": {"hts": "520100", "duty": 0}
            },
            quality_standards=["USDA", "BCI"],
            major_producing_countries=["India", "USA", "China"],
            phytosanitary_required=True,
            fumigation_required=True,
            seasonal_commodity=True,
            harvest_season={"India": ["Oct", "Nov", "Dec"]},
            standard_lot_size={"domestic": {"value": 25, "unit": "BALES"}}
        )
        
        assert data.default_currency == "USD"
        assert len(data.supported_currencies) == 3
        assert data.international_pricing_unit == "CENTS_PER_POUND"
        assert data.hs_code_6digit == "520100"
        assert "USDA" in data.quality_standards
        assert data.phytosanitary_required is True
        assert data.seasonal_commodity is True
    
    def test_commodity_update_partial_international_fields(self):
        """Test updating only some international fields"""
        data = CommodityUpdate(
            default_currency="EUR",
            supported_currencies=["EUR", "USD"],
            international_pricing_unit="EUR_PER_KG"
        )
        
        assert data.default_currency == "EUR"
        assert data.name is None  # Other fields remain None
        assert data.hsn_code is None
    
    def test_invalid_currency_code_length(self):
        """Test that currency codes should be 3 characters (note: not enforced by schema)"""
        # Note: Currency code validation is lenient in current schema
        # This test documents expected behavior for future enhancement
        data = CommodityCreate(
            name="Test Commodity",
            category="Test",
            default_currency="US"  # Less than 3 chars - currently allowed
        )
        
        # Currently passes - future enhancement could add stricter validation
        assert data.default_currency == "US"
    
    def test_tolerance_percentages_validation(self):
        """Test delivery and weight tolerance must be 0-100"""
        with pytest.raises(ValidationError):
            CommodityCreate(
                name="Test",
                category="Test",
                delivery_tolerance_pct=Decimal("150")  # > 100
            )
        
        with pytest.raises(ValidationError):
            CommodityCreate(
                name="Test",
                category="Test",
                weight_tolerance_pct=Decimal("-5")  # < 0
            )


class TestAISuggestionTemplates:
    """Test AI template suggestions for commodities"""
    
    @pytest.mark.asyncio
    async def test_cotton_template_suggestion(self):
        """Test Cotton template returns correct fields"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("Cotton", "Natural Fiber")
        
        assert result["confidence"] == 0.95
        assert result["template_used"] == "Cotton"
        
        fields = result["international_fields"]
        assert fields["default_currency"] == "USD"
        assert fields["international_pricing_unit"] == "CENTS_PER_POUND"
        assert fields["hs_code_6digit"] == "520100"
        assert "USDA" in fields["quality_standards"]
        assert "BCI" in fields["quality_standards"]
        assert "MCX" in fields["traded_on_exchanges"]
        assert "ICE_Futures" in fields["traded_on_exchanges"]
        assert fields["phytosanitary_required"] is True
        assert fields["fumigation_required"] is True
        assert fields["seasonal_commodity"] is True
        assert "India" in fields["harvest_season"]
        assert "Oct" in fields["harvest_season"]["India"]
    
    @pytest.mark.asyncio
    async def test_wheat_template_suggestion(self):
        """Test Wheat template"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("Wheat")
        
        assert result["confidence"] == 0.95
        assert result["template_used"] == "Wheat"
        
        fields = result["international_fields"]
        assert fields["international_pricing_unit"] == "USD_PER_MT"
        assert fields["hs_code_6digit"] == "100190"
        assert "USDA" in fields["quality_standards"]
        assert "CBOT" in fields["traded_on_exchanges"]
        assert fields["export_regulations"]["license_required"] is True
    
    @pytest.mark.asyncio
    async def test_gold_template_suggestion(self):
        """Test Gold template"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("Gold")
        
        assert result["confidence"] == 0.95
        assert result["template_used"] == "Gold"
        
        fields = result["international_fields"]
        assert fields["international_pricing_unit"] == "USD_PER_TROY_OUNCE"
        assert fields["hs_code_6digit"] == "710812"
        assert "LBMA" in fields["quality_standards"]
        assert "COMEX" in fields["traded_on_exchanges"]
        assert fields["seasonal_commodity"] is False
        assert fields["storage_conditions"]["vault_storage"] is True
    
    @pytest.mark.asyncio
    async def test_rice_template_suggestion(self):
        """Test Rice template"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("Rice")
        
        assert result["confidence"] == 0.95
        assert result["template_used"] == "Rice"
        
        fields = result["international_fields"]
        assert fields["hs_code_6digit"] == "100630"
        assert "Codex_Alimentarius" in fields["quality_standards"]
        assert "NCDEX" in fields["traded_on_exchanges"]
        assert "Basmati" in fields["international_grades"]["Type"]
    
    @pytest.mark.asyncio
    async def test_silver_template_suggestion(self):
        """Test Silver template"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("Silver")
        
        assert result["confidence"] == 0.95
        assert result["template_used"] == "Silver"
        
        fields = result["international_fields"]
        assert fields["hs_code_6digit"] == "710691"
        assert fields["price_volatility"] == "HIGH"
        assert "999 (Fine)" in fields["international_grades"]["Purity"]
    
    @pytest.mark.asyncio
    async def test_copper_template_suggestion(self):
        """Test Copper template"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("Copper")
        
        assert result["confidence"] == 0.95
        assert result["template_used"] == "Copper"
        
        fields = result["international_fields"]
        assert fields["hs_code_6digit"] == "740311"
        assert "LME" in fields["quality_standards"]
        assert "LME" in fields["traded_on_exchanges"]
    
    @pytest.mark.asyncio
    async def test_soybean_oil_template_suggestion(self):
        """Test Soybean Oil template"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("Soybean Oil")
        
        assert result["confidence"] == 0.95
        assert result["template_used"] == "Soybean Oil"
        
        fields = result["international_fields"]
        assert fields["hs_code_6digit"] == "150710"
        assert "CBOT" in fields["traded_on_exchanges"]
        assert fields["seasonal_commodity"] is True
    
    @pytest.mark.asyncio
    async def test_default_fallback_template(self):
        """Test default template for unknown commodity"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("Bananas", "Fruits")
        
        assert result["confidence"] == 0.4
        assert result["template_used"] == "DEFAULT"
        
        fields = result["international_fields"]
        assert fields["default_currency"] == "USD"
        assert fields["international_pricing_unit"] == "USD_PER_KG"
        assert fields["hs_code_6digit"] is None
        assert fields["quality_standards"] == []
    
    @pytest.mark.asyncio
    async def test_template_matching_case_insensitive(self):
        """Test template matching works regardless of case"""
        helper = CommodityAIHelper()
        
        result1 = await helper.suggest_international_fields("cotton")
        result2 = await helper.suggest_international_fields("COTTON")
        result3 = await helper.suggest_international_fields("Cotton")
        
        assert result1["template_used"] == "Cotton"
        assert result2["template_used"] == "Cotton"
        assert result3["template_used"] == "Cotton"
    
    @pytest.mark.asyncio
    async def test_template_matching_with_variants(self):
        """Test template matches commodity variants"""
        helper = CommodityAIHelper()
        
        # Should match Cotton template
        result = await helper.suggest_international_fields("Cotton Lint")
        assert result["template_used"] == "Cotton"
        
        # Should match Wheat template
        result = await helper.suggest_international_fields("Wheat Grain")
        assert result["template_used"] == "Wheat"


class TestCurrencyIntegration:
    """Test currency conversion integration"""
    
    @pytest.mark.asyncio
    async def test_price_conversion_usd_to_inr(self):
        """Test converting USD price to INR"""
        service = CommodityPricingService()
        result = await service.convert_commodity_price(
            price=Decimal("100"),
            from_currency="USD",
            to_currency="INR"
        )
        
        assert result["original_currency"] == "USD"
        assert result["converted_currency"] == "INR"
        assert result["original_price"] == 100.0
        assert result["converted_price"] > 8000  # USD to INR should be ~83x
        assert "exchange_rate" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_same_currency_conversion(self):
        """Test converting USD to USD returns same amount"""
        service = CommodityPricingService()
        result = await service.convert_commodity_price(
            price=Decimal("100"),
            from_currency="USD",
            to_currency="USD"
        )
        
        assert result["original_price"] == 100.0
        assert result["converted_price"] == 100.0
        assert result["exchange_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_multiple_currency_conversion(self):
        """Test converting to multiple currencies"""
        service = CommodityPricingService()
        result = await service.get_price_in_multiple_currencies(
            price=Decimal("1000"),
            base_currency="USD",
            target_currencies=["INR", "EUR", "GBP"]
        )
        
        assert result["base"]["amount"] == 1000.0
        assert result["base"]["currency"] == "USD"
        assert "INR" in result["conversions"]
        assert "EUR" in result["conversions"]
        assert "GBP" in result["conversions"]
        assert result["conversions"]["INR"]["amount"] > 80000  # ~83x
        assert result["conversions"]["EUR"]["amount"] < 1000  # ~0.92x
        assert result["conversions"]["GBP"]["amount"] < 1000  # ~0.79x
    
    @pytest.mark.asyncio
    async def test_cents_per_pound_conversion(self):
        """Test converting KG price to cents per pound"""
        service = CommodityPricingService()
        cents_per_lb = await service.calculate_cents_per_pound(
            price_per_kg=Decimal("2.00")  # $2 per kg
        )
        
        # $2/kg = $0.9072/lb = 90.72 cents/lb
        assert cents_per_lb == Decimal("90.72")
    
    @pytest.mark.asyncio
    async def test_cents_per_pound_reverse_conversion(self):
        """Test converting cents per pound back to KG price"""
        service = CommodityPricingService()
        price_per_kg = await service.calculate_kg_from_cents_per_pound(
            cents_per_pound=Decimal("90.72")
        )
        
        assert price_per_kg == Decimal("2.00")
    
    def test_supported_currencies_list(self):
        """Test getting supported currencies"""
        service = CommodityPricingService()
        currencies = service.get_supported_currencies()
        
        assert "USD" in currencies
        assert "INR" in currencies
        assert "EUR" in currencies
        assert "GBP" in currencies
        assert "CNY" in currencies
        assert len(currencies) >= 30


class TestInternationalFieldsSuggestionSchema:
    """Test the AI suggestion response schema"""
    
    def test_valid_suggestion_schema(self):
        """Test valid suggestion schema validation"""
        data = InternationalFieldsSuggestion(
            confidence=0.95,
            template_used="Cotton",
            international_fields={
                "default_currency": "USD",
                "hs_code_6digit": "520100",
                "quality_standards": ["USDA", "BCI"]
            }
        )
        
        assert data.confidence == 0.95
        assert data.template_used == "Cotton"
        assert data.international_fields["default_currency"] == "USD"
    
    def test_confidence_out_of_range(self):
        """Test confidence must be between 0 and 1"""
        with pytest.raises(ValidationError):
            InternationalFieldsSuggestion(
                confidence=1.5,  # > 1.0
                template_used="Test",
                international_fields={}
            )
        
        with pytest.raises(ValidationError):
            InternationalFieldsSuggestion(
                confidence=-0.1,  # < 0.0
                template_used="Test",
                international_fields={}
            )
    
    def test_empty_international_fields_allowed(self):
        """Test empty international fields dict is valid"""
        data = InternationalFieldsSuggestion(
            confidence=0.4,
            template_used="DEFAULT",
            international_fields={}
        )
        
        assert data.international_fields == {}


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_empty_commodity_name(self):
        """Test empty commodity name uses default template"""
        helper = CommodityAIHelper()
        result = await helper.suggest_international_fields("", "")
        
        assert result["template_used"] == "DEFAULT"
        assert result["confidence"] == 0.4
    
    @pytest.mark.asyncio
    async def test_very_long_commodity_name(self):
        """Test very long commodity name"""
        helper = CommodityAIHelper()
        long_name = "A" * 500  # 500 character name
        result = await helper.suggest_international_fields(long_name)
        
        # Should still work and return DEFAULT template
        assert "template_used" in result
        assert "international_fields" in result
    
    def test_country_tax_codes_json_structure(self):
        """Test country tax codes JSON structure validation"""
        data = CommodityCreate(
            name="Test",
            category="Test",
            country_tax_codes={
                "IND": {
                    "hsn": "5201",
                    "gst": 5.0
                },
                "USA": {
                    "hts": "520100",
                    "duty": 0
                }
            }
        )
        
        assert data.country_tax_codes["IND"]["hsn"] == "5201"
        assert data.country_tax_codes["USA"]["hts"] == "520100"
    
    def test_harvest_season_json_structure(self):
        """Test harvest season JSON structure"""
        data = CommodityCreate(
            name="Test",
            category="Test",
            harvest_season={
                "India": ["Oct", "Nov", "Dec"],
                "USA": ["Aug", "Sep"],
                "China": ["Sep", "Oct", "Nov"]
            }
        )
        
        assert len(data.harvest_season["India"]) == 3
        assert "Oct" in data.harvest_season["India"]
        assert len(data.harvest_season["USA"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
