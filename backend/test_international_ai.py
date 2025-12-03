"""
Test International Commodity AI Suggestions

Quick test to validate AI templates for Cotton, Wheat, Gold
"""

import asyncio
from backend.modules.settings.commodities.ai_helpers import CommodityAIHelper


async def test_cotton_suggestion():
    """Test Cotton template"""
    print("\n" + "="*80)
    print("TESTING: Cotton Template")
    print("="*80)
    
    helper = CommodityAIHelper()
    result = await helper.suggest_international_fields("Cotton", "Natural Fiber")
    
    print(f"Confidence: {result['confidence']}")
    print(f"Template Used: {result['template_used']}")
    print(f"\nInternational Fields Preview:")
    fields = result['international_fields']
    print(f"  Default Currency: {fields['default_currency']}")
    print(f"  Supported Currencies: {fields['supported_currencies']}")
    print(f"  Pricing Unit: {fields['international_pricing_unit']}")
    print(f"  HS Code: {fields['hs_code_6digit']}")
    print(f"  Quality Standards: {fields['quality_standards']}")
    print(f"  Major Producers: {fields['major_producing_countries']}")
    print(f"  Exchanges: {fields['traded_on_exchanges']}")
    print(f"  Phytosanitary Required: {fields['phytosanitary_required']}")
    print(f"  Seasonal: {fields['seasonal_commodity']}")
    print(f"  Harvest Seasons: {fields['harvest_season']}")
    
    assert result['confidence'] == 0.95
    assert result['template_used'] == "Cotton"
    assert fields['default_currency'] == "USD"
    assert fields['international_pricing_unit'] == "CENTS_PER_POUND"
    assert fields['hs_code_6digit'] == "520100"
    assert "USDA" in fields['quality_standards']
    assert "MCX" in fields['traded_on_exchanges']
    print("\n✅ Cotton template test PASSED")


async def test_wheat_suggestion():
    """Test Wheat template"""
    print("\n" + "="*80)
    print("TESTING: Wheat Template")
    print("="*80)
    
    helper = CommodityAIHelper()
    result = await helper.suggest_international_fields("Wheat", "Grains")
    
    print(f"Confidence: {result['confidence']}")
    print(f"Template Used: {result['template_used']}")
    print(f"\nInternational Fields Preview:")
    fields = result['international_fields']
    print(f"  Default Currency: {fields['default_currency']}")
    print(f"  Supported Currencies: {fields['supported_currencies']}")
    print(f"  Pricing Unit: {fields['international_pricing_unit']}")
    print(f"  HS Code: {fields['hs_code_6digit']}")
    print(f"  Quality Standards: {fields['quality_standards']}")
    print(f"  Major Producers: {fields['major_producing_countries']}")
    print(f"  Exchanges: {fields['traded_on_exchanges']}")
    print(f"  Export License Required: {fields['export_regulations']['license_required']}")
    
    assert result['confidence'] == 0.95
    assert result['template_used'] == "Wheat"
    assert fields['default_currency'] == "USD"
    assert fields['international_pricing_unit'] == "USD_PER_MT"
    assert fields['hs_code_6digit'] == "100190"
    assert "USDA" in fields['quality_standards']
    assert "CBOT" in fields['traded_on_exchanges']
    print("\n✅ Wheat template test PASSED")


async def test_gold_suggestion():
    """Test Gold template"""
    print("\n" + "="*80)
    print("TESTING: Gold Template")
    print("="*80)
    
    helper = CommodityAIHelper()
    result = await helper.suggest_international_fields("Gold", "Precious Metals")
    
    print(f"Confidence: {result['confidence']}")
    print(f"Template Used: {result['template_used']}")
    print(f"\nInternational Fields Preview:")
    fields = result['international_fields']
    print(f"  Default Currency: {fields['default_currency']}")
    print(f"  Supported Currencies: {fields['supported_currencies']}")
    print(f"  Pricing Unit: {fields['international_pricing_unit']}")
    print(f"  HS Code: {fields['hs_code_6digit']}")
    print(f"  Quality Standards: {fields['quality_standards']}")
    print(f"  Major Producers: {fields['major_producing_countries']}")
    print(f"  Exchanges: {fields['traded_on_exchanges']}")
    print(f"  Storage Conditions: {fields['storage_conditions']}")
    print(f"  Seasonal: {fields['seasonal_commodity']}")
    
    assert result['confidence'] == 0.95
    assert result['template_used'] == "Gold"
    assert fields['default_currency'] == "USD"
    assert fields['international_pricing_unit'] == "USD_PER_TROY_OUNCE"
    assert fields['hs_code_6digit'] == "710812"
    assert "LBMA" in fields['quality_standards']
    assert "COMEX" in fields['traded_on_exchanges']
    assert fields['seasonal_commodity'] is False
    print("\n✅ Gold template test PASSED")


async def test_unknown_commodity():
    """Test default fallback for unknown commodity"""
    print("\n" + "="*80)
    print("TESTING: Unknown Commodity (Default Template)")
    print("="*80)
    
    helper = CommodityAIHelper()
    result = await helper.suggest_international_fields("Bananas", "Fruits")
    
    print(f"Confidence: {result['confidence']}")
    print(f"Template Used: {result['template_used']}")
    print(f"\nInternational Fields Preview:")
    fields = result['international_fields']
    print(f"  Default Currency: {fields['default_currency']}")
    print(f"  Pricing Unit: {fields['international_pricing_unit']}")
    print(f"  HS Code: {fields['hs_code_6digit']}")
    
    assert result['confidence'] == 0.4
    assert result['template_used'] == "DEFAULT"
    assert fields['default_currency'] == "USD"
    assert fields['international_pricing_unit'] == "USD_PER_KG"
    assert fields['hs_code_6digit'] is None
    print("\n✅ Unknown commodity fallback test PASSED")


async def test_rice_suggestion():
    """Test Rice template"""
    print("\n" + "="*80)
    print("TESTING: Rice Template")
    print("="*80)
    
    helper = CommodityAIHelper()
    result = await helper.suggest_international_fields("Rice", "Grains")
    
    print(f"Confidence: {result['confidence']}")
    print(f"Template Used: {result['template_used']}")
    print(f"\nInternational Fields Preview:")
    fields = result['international_fields']
    print(f"  Default Currency: {fields['default_currency']}")
    print(f"  Supported Currencies: {fields['supported_currencies']}")
    print(f"  Pricing Unit: {fields['international_pricing_unit']}")
    print(f"  HS Code: {fields['hs_code_6digit']}")
    print(f"  Quality Standards: {fields['quality_standards']}")
    print(f"  International Grades: {list(fields['international_grades'].keys())}")
    print(f"  Major Producers: {fields['major_producing_countries'][:3]}")
    print(f"  Exchanges: {fields['traded_on_exchanges']}")
    
    assert result['confidence'] == 0.95
    assert result['template_used'] == "Rice"
    assert fields['default_currency'] == "USD"
    assert fields['hs_code_6digit'] == "100630"
    assert "Codex_Alimentarius" in fields['quality_standards']
    assert "NCDEX" in fields['traded_on_exchanges']
    print("\n✅ Rice template test PASSED")


async def test_silver_suggestion():
    """Test Silver template"""
    print("\n" + "="*80)
    print("TESTING: Silver Template")
    print("="*80)
    
    helper = CommodityAIHelper()
    result = await helper.suggest_international_fields("Silver", "Precious Metals")
    
    print(f"Confidence: {result['confidence']}")
    print(f"Template Used: {result['template_used']}")
    print(f"\nInternational Fields Preview:")
    fields = result['international_fields']
    print(f"  Default Currency: {fields['default_currency']}")
    print(f"  Pricing Unit: {fields['international_pricing_unit']}")
    print(f"  HS Code: {fields['hs_code_6digit']}")
    print(f"  Quality Standards: {fields['quality_standards']}")
    print(f"  Purity Grades: {fields['international_grades']['Purity']}")
    print(f"  Exchanges: {fields['traded_on_exchanges']}")
    print(f"  Price Volatility: {fields['price_volatility']}")
    
    assert result['confidence'] == 0.95
    assert result['template_used'] == "Silver"
    assert fields['international_pricing_unit'] == "USD_PER_TROY_OUNCE"
    assert fields['hs_code_6digit'] == "710691"
    assert "LBMA" in fields['quality_standards']
    assert fields['price_volatility'] == "HIGH"
    print("\n✅ Silver template test PASSED")


async def test_copper_suggestion():
    """Test Copper template"""
    print("\n" + "="*80)
    print("TESTING: Copper Template")
    print("="*80)
    
    helper = CommodityAIHelper()
    result = await helper.suggest_international_fields("Copper", "Base Metals")
    
    print(f"Confidence: {result['confidence']}")
    print(f"Template Used: {result['template_used']}")
    print(f"\nInternational Fields Preview:")
    fields = result['international_fields']
    print(f"  Default Currency: {fields['default_currency']}")
    print(f"  Pricing Unit: {fields['international_pricing_unit']}")
    print(f"  HS Code: {fields['hs_code_6digit']}")
    print(f"  Quality Standards: {fields['quality_standards']}")
    print(f"  Grades: {fields['international_grades']['Grade']}")
    print(f"  Major Producers: {fields['major_producing_countries'][:3]}")
    print(f"  Exchanges: {fields['traded_on_exchanges']}")
    
    assert result['confidence'] == 0.95
    assert result['template_used'] == "Copper"
    assert fields['international_pricing_unit'] == "USD_PER_MT"
    assert fields['hs_code_6digit'] == "740311"
    assert "LME" in fields['quality_standards']
    assert "LME" in fields['traded_on_exchanges']
    print("\n✅ Copper template test PASSED")


async def test_soybean_oil_suggestion():
    """Test Soybean Oil template"""
    print("\n" + "="*80)
    print("TESTING: Soybean Oil Template")
    print("="*80)
    
    helper = CommodityAIHelper()
    result = await helper.suggest_international_fields("Soybean Oil", "Edible Oils")
    
    print(f"Confidence: {result['confidence']}")
    print(f"Template Used: {result['template_used']}")
    print(f"\nInternational Fields Preview:")
    fields = result['international_fields']
    print(f"  Default Currency: {fields['default_currency']}")
    print(f"  Pricing Unit: {fields['international_pricing_unit']}")
    print(f"  HS Code: {fields['hs_code_6digit']}")
    print(f"  Quality Standards: {fields['quality_standards']}")
    print(f"  Types: {fields['international_grades']['Type']}")
    print(f"  Major Producers: {fields['major_producing_countries'][:3]}")
    print(f"  Exchanges: {fields['traded_on_exchanges']}")
    print(f"  Seasonal: {fields['seasonal_commodity']}")
    
    assert result['confidence'] == 0.95
    assert result['template_used'] == "Soybean Oil"
    assert fields['international_pricing_unit'] == "USD_PER_MT"
    assert fields['hs_code_6digit'] == "150710"
    assert "Codex_Alimentarius" in fields['quality_standards']
    assert "CBOT" in fields['traded_on_exchanges']
    print("\n✅ Soybean Oil template test PASSED")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("INTERNATIONAL COMMODITY AI SUGGESTION TESTS")
    print("="*80)
    
    try:
        await test_cotton_suggestion()
        await test_wheat_suggestion()
        await test_gold_suggestion()
        await test_rice_suggestion()
        await test_silver_suggestion()
        await test_copper_suggestion()
        await test_soybean_oil_suggestion()
        await test_unknown_commodity()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✅")
        print("="*80)
        print("\nSummary:")
        print("  - Cotton template: ✅ 95% confidence")
        print("  - Wheat template: ✅ 95% confidence")
        print("  - Gold template: ✅ 95% confidence")
        print("  - Rice template: ✅ 95% confidence")
        print("  - Silver template: ✅ 95% confidence")
        print("  - Copper template: ✅ 95% confidence")
        print("  - Soybean Oil template: ✅ 95% confidence")
        print("  - Default fallback: ✅ 40% confidence")
        print("\n🎉 7 commodity templates with 90% AI automation!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
