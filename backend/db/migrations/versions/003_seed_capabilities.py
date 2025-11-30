"""seed_capabilities

Revision ID: 003_seed_capabilities
Revises: 002_capabilities
Create Date: 2025-11-30

"""
from alembic import op
import uuid

# revision identifiers, used by Alembic.
revision = '003_seed_capabilities'
down_revision = '002_capabilities'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Seed all capabilities defined in backend.core.auth.capabilities.definitions"""
    
    # Import after tables are created
    from backend.core.auth.capabilities.definitions import CAPABILITY_METADATA, Capabilities
    
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
    
    # Bulk insert
    op.bulk_insert(
        op.get_bind().dialect.get_table(op.get_bind(), "capabilities"),
        capabilities_data
    )


def downgrade() -> None:
    """Remove seeded capabilities"""
    op.execute("DELETE FROM capabilities")
