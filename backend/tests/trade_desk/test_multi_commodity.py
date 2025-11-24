"""
Integration Tests - Multi-Commodity Support

Tests:
- Cotton with cotton-specific quality params
- Gold with gold-specific quality params
- Wheat with wheat-specific quality params
- JSONB flexibility validation
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.modules.trade_desk.services.availability_service import AvailabilityService
from backend.modules.trade_desk.enums import MarketVisibility


@pytest.mark.asyncio
class TestMultiCommoditySupport:
    """Test universal JSONB schema works across different commodities."""
    
    async def test_cotton_availability(
        self,
        async_db,
        sample_commodity,
        sample_location,
        sample_seller,
        mock_user,
        cotton_quality_params
    ):
        """Test creating cotton availability with cotton-specific params."""
        service = AvailabilityService(async_db)
        
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("10000"),
            base_price=Decimal("75000"),
            price_matrix={
                "29mm": 75000,
                "30mm": 77000,
                "28mm": 73000,
                "31mm": 79000
            },
            quality_params=cotton_quality_params,
            market_visibility=MarketVisibility.PUBLIC,
            allow_partial_order=True,
            min_order_quantity=Decimal("500"),
            delivery_terms="EX-WAREHOUSE",
            delivery_address="Cotton Warehouse, Gujarat",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
            created_by=mock_user.id
        )
        
        assert availability.id is not None
        assert availability.quality_params["staple_length"] == "29mm"
        assert availability.quality_params["micronaire"] == "3.5-4.5"
        assert availability.quality_params["strength"] == "28-30 g/tex"
        assert availability.price_matrix["29mm"] == 75000
        assert availability.price_matrix["30mm"] == 77000
    
    async def test_gold_availability(
        self,
        async_db,
        sample_gold_commodity,
        sample_location,
        sample_seller,
        mock_user,
        gold_quality_params
    ):
        """Test creating gold availability with gold-specific params."""
        service = AvailabilityService(async_db)
        
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_gold_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("10000"),  # 10 kg in grams
            base_price=Decimal("6500000"),  # per kg
            price_matrix={
                "1kg_bar": 6500000,
                "500g_bar": 3250000,
                "100g_bar": 650000,
                "10g_coin": 65000
            },
            quality_params=gold_quality_params,
            market_visibility=MarketVisibility.RESTRICTED,
            allow_partial_order=False,  # Gold usually sold in standard units
            min_order_quantity=Decimal("1000"),  # Minimum 1 kg
            delivery_terms="VAULT_TRANSFER",
            delivery_address="Secured Vault, Mumbai",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=mock_user.id
        )
        
        assert availability.id is not None
        assert availability.quality_params["purity"] == "99.99%"
        assert availability.quality_params["form"] == "bar"
        assert availability.quality_params["certification"] == "LBMA"
        assert availability.price_matrix["1kg_bar"] == 6500000
        assert availability.allow_partial_order is False
    
    async def test_wheat_availability(
        self,
        async_db,
        sample_wheat_commodity,
        sample_location,
        sample_seller,
        mock_user,
        wheat_quality_params
    ):
        """Test creating wheat availability with wheat-specific params."""
        service = AvailabilityService(async_db)
        
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_wheat_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("50000"),  # 50 tons
            base_price=Decimal("2500"),  # per kg
            price_matrix={
                "premium": 2700,
                "standard": 2500,
                "economy": 2300
            },
            quality_params=wheat_quality_params,
            market_visibility=MarketVisibility.PUBLIC,
            allow_partial_order=True,
            min_order_quantity=Decimal("1000"),  # Minimum 1 ton
            delivery_terms="FCA_PORT",
            delivery_address="APMC Market, Punjab",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=60),
            created_by=mock_user.id
        )
        
        assert availability.id is not None
        assert availability.quality_params["variety"] == "PBW 343"
        assert availability.quality_params["moisture"] == "12%"
        assert availability.quality_params["test_weight"] == "78 kg/hl"
        assert availability.price_matrix["premium"] == 2700
        assert availability.price_matrix["standard"] == 2500
    
    async def test_search_cotton_by_quality(
        self,
        async_db,
        sample_commodity,
        sample_location,
        sample_seller,
        mock_user,
        mock_buyer_user,
        cotton_quality_params
    ):
        """Test searching cotton by specific quality parameters."""
        service = AvailabilityService(async_db)
        
        # Create cotton availability
        await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("5000"),
            base_price=Decimal("75000"),
            quality_params=cotton_quality_params,
            market_visibility=MarketVisibility.PUBLIC,
            allow_partial_order=True,
            min_order_quantity=Decimal("500"),
            delivery_terms="EX-WAREHOUSE",
            delivery_address="Test",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
            created_by=mock_user.id
        )
        
        # Search by quality
        results = await service.search_availabilities(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            quality_params={"staple_length": "29mm"},
            quality_tolerance=0.1
        )
        
        assert len(results) >= 1
        # Verify matching availability found
        assert results[0]["availability"].quality_params["staple_length"] == "29mm"
    
    async def test_search_gold_by_purity(
        self,
        async_db,
        sample_gold_commodity,
        sample_location,
        sample_seller,
        mock_user,
        mock_buyer_user,
        gold_quality_params
    ):
        """Test searching gold by purity."""
        service = AvailabilityService(async_db)
        
        # Create gold availability
        await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_gold_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("5000"),
            base_price=Decimal("6500000"),
            quality_params=gold_quality_params,
            market_visibility=MarketVisibility.PUBLIC,
            allow_partial_order=False,
            min_order_quantity=Decimal("1000"),
            delivery_terms="VAULT_TRANSFER",
            delivery_address="Test",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=mock_user.id
        )
        
        # Search by purity
        results = await service.search_availabilities(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_gold_commodity.id,
            quality_params={"purity": "99.99%"}
        )
        
        assert len(results) >= 1
        assert results[0]["availability"].quality_params["purity"] == "99.99%"
    
    async def test_jsonb_flexibility_different_schemas(
        self,
        async_db,
        sample_commodity,
        sample_gold_commodity,
        sample_wheat_commodity,
        sample_location,
        sample_seller,
        mock_user
    ):
        """Test that different commodities can have completely different quality param schemas."""
        service = AvailabilityService(async_db)
        
        # Cotton with cotton schema
        cotton_av = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("1000"),
            base_price=Decimal("75000"),
            quality_params={
                "staple_length": "29mm",
                "micronaire": "3.5-4.5",
                "strength": "28-30 g/tex"
            },
            market_visibility=MarketVisibility.PUBLIC,
            allow_partial_order=True,
            min_order_quantity=Decimal("100"),
            delivery_terms="EX-WAREHOUSE",
            delivery_address="Test",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
            created_by=mock_user.id
        )
        
        # Gold with completely different schema
        gold_av = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_gold_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("1000"),
            base_price=Decimal("6500000"),
            quality_params={
                "purity": "99.99%",
                "form": "bar",
                "certification": "LBMA",
                "serial_number": "XYZ123"
            },
            market_visibility=MarketVisibility.PUBLIC,
            allow_partial_order=False,
            min_order_quantity=Decimal("1000"),
            delivery_terms="VAULT_TRANSFER",
            delivery_address="Test",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=mock_user.id
        )
        
        # Wheat with yet another schema
        wheat_av = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_wheat_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("5000"),
            base_price=Decimal("2500"),
            quality_params={
                "variety": "PBW 343",
                "moisture": "12%",
                "protein_content": "11.5%"
            },
            market_visibility=MarketVisibility.PUBLIC,
            allow_partial_order=True,
            min_order_quantity=Decimal("1000"),
            delivery_terms="FCA_PORT",
            delivery_address="Test",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=60),
            created_by=mock_user.id
        )
        
        # Verify all created successfully with different schemas
        assert cotton_av.quality_params["staple_length"] == "29mm"
        assert "micronaire" in cotton_av.quality_params
        
        assert gold_av.quality_params["purity"] == "99.99%"
        assert "certification" in gold_av.quality_params
        
        assert wheat_av.quality_params["variety"] == "PBW 343"
        assert "protein_content" in wheat_av.quality_params
        
        # No overlapping keys between schemas
        cotton_keys = set(cotton_av.quality_params.keys())
        gold_keys = set(gold_av.quality_params.keys())
        wheat_keys = set(wheat_av.quality_params.keys())
        
        assert cotton_keys.isdisjoint(gold_keys)
        assert gold_keys.isdisjoint(wheat_keys)
