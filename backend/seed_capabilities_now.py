"""
Quick script to seed capabilities into database
Run this to populate the capabilities table
"""
import asyncio
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.auth.capabilities.definitions import CAPABILITY_METADATA, Capabilities

DATABASE_URL = "postgresql+asyncpg://cotton_user:commodity_password@localhost:5432/cotton_erp"


async def seed_capabilities():
    """Seed all capabilities into database"""
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    capabilities_data = []
    for capability in Capabilities:
        metadata = CAPABILITY_METADATA.get(capability, {
            "name": capability.value.replace("_", " ").title(),
            "description": f"Capability: {capability.value}",
            "category": capability.value.split("_")[0].lower(),
            "is_system": False,
        })
        
        capabilities_data.append({
            "id": str(uuid.uuid4()),
            "code": capability.value,
            "name": metadata.get("name", capability.value),
            "description": metadata.get("description", ""),
            "category": metadata.get("category", "system"),
            "is_system": metadata.get("is_system", False),
        })
    
    print(f"\n🌱 Seeding {len(capabilities_data)} capabilities...")
    
    async with engine.begin() as conn:
        # Check if already seeded
        result = await conn.execute(text("SELECT COUNT(*) FROM capabilities"))
        existing_count = result.scalar()
        
        if existing_count > 0:
            print(f"⚠️  Found {existing_count} existing capabilities. Skipping seed.")
            print("   Run: docker exec commodity-erp-postgres psql -U cotton_user -d cotton_erp -c 'DELETE FROM capabilities;'")
            print("   to clear and re-seed.")
            return
        
        # Bulk insert
        for cap in capabilities_data:
            await conn.execute(
                text("""
                    INSERT INTO capabilities (id, code, name, description, category, is_system, created_at, updated_at)
                    VALUES (:id, :code, :name, :description, :category, :is_system, NOW(), NOW())
                """),
                cap
            )
        
        print(f"✅ Successfully seeded {len(capabilities_data)} capabilities!")
        
        # Show breakdown by category
        result = await conn.execute(text("""
            SELECT category, COUNT(*) as count 
            FROM capabilities 
            GROUP BY category 
            ORDER BY category
        """))
        
        print("\n📊 Capabilities by category:")
        for row in result:
            print(f"   {row.category}: {row.count}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_capabilities())
