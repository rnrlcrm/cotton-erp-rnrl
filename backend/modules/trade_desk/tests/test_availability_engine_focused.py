"""
Focused Availability Engine Test - Production Ready
Tests core functionality without complex fixtures
"""
import pytest
import asyncio
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import text

from backend.core.database import engine, get_db
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.trade_desk.schemas import AvailabilityCreate


@pytest.mark.asyncio
class TestAvailabilityEngineCore:
    """Test core availability engine functionality"""
    
    async def test_database_schema_location_nullable(self):
        """Test 1: Verify location_id is nullable in database schema"""
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name='availabilities' AND column_name='location_id'
            """))
            row = result.fetchone()
            assert row is not None, "location_id column not found"
            assert row[0] == 'YES', "location_id should be nullable"
    
    async def test_migration_applied(self):
        """Test 2: Verify migration 6827270c0b0b is applied"""
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT version_num FROM alembic_version
            """))
            row = result.fetchone()
            assert row is not None, "No alembic version found"
            assert row[0] == '6827270c0b0b', f"Expected migration 6827270c0b0b but got {row[0]}"
    
    async def test_availability_model_location_nullable(self):
        """Test 3: Verify Availability model has nullable location_id"""
        from backend.modules.trade_desk.models.availability import Availability
        
        # Check location_id column is nullable
        location_id_col = Availability.__table__.columns['location_id']
        assert location_id_col.nullable == True, "location_id should be nullable in model"
    
    async def test_schema_validation_adhoc_location(self):
        """Test 4: Verify schema accepts ad-hoc location fields"""
        from backend.modules.trade_desk.schemas import AvailabilityCreate
        from pydantic import ValidationError
        
        # Valid ad-hoc location (no location_id)
        data = {
            "seller_id": str(uuid4()),
            "commodity_id": str(uuid4()),
            "total_quantity": Decimal("100.0"),
            "location_address": "Warehouse 5, GIDC Surat",
            "location_latitude": Decimal("21.1702"),
            "location_longitude": Decimal("72.8311"),
            "location_region": "Gujarat",
            "quality_params": {"length": "29mm"}
        }
        
        # Should not raise validation error
        schema = AvailabilityCreate(**data)
        assert schema.location_id is None
        assert schema.location_address == "Warehouse 5, GIDC Surat"
        assert schema.location_latitude == Decimal("21.1702")
        assert schema.location_longitude == Decimal("72.8311")
    
    async def test_schema_validation_registered_location(self):
        """Test 5: Verify schema accepts registered location"""
        from backend.modules.trade_desk.schemas import AvailabilityCreate
        
        location_id = uuid4()
        data = {
            "seller_id": str(uuid4()),
            "commodity_id": str(uuid4()),
            "total_quantity": Decimal("100.0"),
            "location_id": str(location_id),
            "quality_params": {"length": "29mm"}
        }
        
        schema = AvailabilityCreate(**data)
        assert schema.location_id == location_id
        assert schema.location_address is None
    
    async def test_schema_validation_rejects_both_location_types(self):
        """Test 6: Verify schema rejects both location_id AND ad-hoc fields"""
        from backend.modules.trade_desk.schemas import AvailabilityCreate
        from pydantic import ValidationError
        
        data = {
            "seller_id": str(uuid4()),
            "commodity_id": str(uuid4()),
            "total_quantity": Decimal("100.0"),
            "location_id": str(uuid4()),  # Registered location
            "location_address": "Warehouse 5",  # Ad-hoc location
            "location_latitude": Decimal("21.1702"),
            "location_longitude": Decimal("72.8311"),
            "quality_params": {"length": "29mm"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityCreate(**data)
        
        assert "Cannot provide both" in str(exc_info.value)
    
    async def test_schema_validation_rejects_neither_location_type(self):
        """Test 7: Verify schema rejects missing location data"""
        from backend.modules.trade_desk.schemas import AvailabilityCreate
        from pydantic import ValidationError
        
        data = {
            "seller_id": str(uuid4()),
            "commodity_id": str(uuid4()),
            "total_quantity": Decimal("100.0"),
            "quality_params": {"length": "29mm"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityCreate(**data)
        
        assert "Must provide either" in str(exc_info.value)
    
    async def test_schema_validation_incomplete_adhoc_location(self):
        """Test 8: Verify schema rejects incomplete ad-hoc location"""
        from backend.modules.trade_desk.schemas import AvailabilityCreate
        from pydantic import ValidationError
        
        # Missing longitude
        data = {
            "seller_id": str(uuid4()),
            "commodity_id": str(uuid4()),
            "total_quantity": Decimal("100.0"),
            "location_address": "Warehouse 5",
            "location_latitude": Decimal("21.1702"),
            # Missing location_longitude
            "quality_params": {"length": "29mm"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityCreate(**data)
        
        assert "incomplete" in str(exc_info.value).lower()
    
    async def test_auto_unit_population_schema(self):
        """Test 9: Verify quantity_unit and price_unit are optional"""
        from backend.modules.trade_desk.schemas import AvailabilityCreate
        
        data = {
            "seller_id": str(uuid4()),
            "commodity_id": str(uuid4()),
            "total_quantity": Decimal("100.0"),
            "location_id": str(uuid4()),
            "quality_params": {"length": "29mm"}
            # NO quantity_unit or price_unit provided
        }
        
        schema = AvailabilityCreate(**data)
        assert schema.quantity_unit is None
        assert schema.price_unit is None
    
    async def test_database_constraint_foreign_key(self):
        """Test 10: Verify location_id has correct foreign key"""
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT 
                    tc.constraint_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_name='availabilities' 
                    AND tc.constraint_type = 'FOREIGN KEY'
                    AND tc.constraint_name LIKE '%location%'
            """))
            row = result.fetchone()
            assert row is not None, "Foreign key constraint not found"
            assert row[1] == 'settings_locations', "Should reference settings_locations table"


@pytest.mark.asyncio
class TestAvailabilityEngineBehavior:
    """Test actual availability engine behavior"""
    
    async def test_availability_table_exists(self):
        """Test 11: Verify availabilities table exists"""
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='availabilities'
            """))
            row = result.fetchone()
            assert row is not None, "availabilities table not found"
    
    async def test_required_columns_exist(self):
        """Test 12: Verify all required columns exist"""
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='availabilities'
                ORDER BY ordinal_position
            """))
            columns = [row[0] for row in result.fetchall()]
            
            required_columns = [
                'id', 'seller_id', 'commodity_id', 'location_id',
                'total_quantity', 'quantity_unit', 'price_unit',
                'delivery_latitude', 'delivery_longitude', 'delivery_address',
                'quality_params', 'status', 'created_at'
            ]
            
            for col in required_columns:
                assert col in columns, f"Required column {col} not found"
    
    async def test_adhoc_location_columns_exist(self):
        """Test 13: Verify ad-hoc location columns exist"""
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='availabilities'
                AND column_name IN ('delivery_latitude', 'delivery_longitude', 'delivery_address', 'delivery_region')
            """))
            columns = [row[0] for row in result.fetchall()]
            
            assert 'delivery_latitude' in columns
            assert 'delivery_longitude' in columns
            assert 'delivery_address' in columns
            assert 'delivery_region' in columns


def run_tests():
    """Run all tests and return pass rate"""
    import subprocess
    import sys
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    print(result.stderr)
    
    return result.returncode


if __name__ == "__main__":
    exit(run_tests())
