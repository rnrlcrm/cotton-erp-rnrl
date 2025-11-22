"""
Seed Data for Data Isolation Testing

Creates test data for all three user types:
- SUPER_ADMIN: Full global access
- INTERNAL: Back-office users (see all business partners)
- EXTERNAL: Business partner users (see only their data)

Usage:
    cd /workspaces/cotton-erp-rnrl/backend
    python scripts/seed_isolation_test_data.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.db.session_module import SessionLocal
from backend.modules.settings.business_partners.models import BusinessPartner
from backend.modules.settings.models.settings_models import User
from backend.modules.settings.organization.models import Organization
from passlib.context import CryptContext

# Use pbkdf2 instead of bcrypt (bcrypt has version issues)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def create_seed_data():
    """Create test business partners and users"""
    
    db: Session = SessionLocal()
    
    try:
        print("🌱 Starting seed data creation...")
        
        # Check if data already exists
        existing_bp = db.query(BusinessPartner).first()
        if existing_bp:
            print("⚠️  Seed data already exists. Skipping...")
            return
        
        # Create default organization for INTERNAL users
        print("\n🏢 Creating Organization...")
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="RNRL Headquarters",
            is_active=True,
        )
        db.add(org)
        db.flush()
        print(f"  ✅ Created: {org.name}")
        
        # Create Business Partners
        print("\n📦 Creating Business Partners...")
        
        bp1_id = uuid4()
        bp1 = BusinessPartner(
            id=bp1_id,
            name="Acme Trading Co.",
            partner_type="BUYER",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            created_by=None,  # System created
        )
        db.add(bp1)
        print(f"  ✅ Created: {bp1.name} ({bp1.partner_type})")
        
        bp2_id = uuid4()
        bp2 = BusinessPartner(
            id=bp2_id,
            name="Global Cotton Suppliers Ltd.",
            partner_type="SELLER",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            created_by=None,
        )
        db.add(bp2)
        print(f"  ✅ Created: {bp2.name} ({bp2.partner_type})")
        
        bp3_id = uuid4()
        bp3 = BusinessPartner(
            id=bp3_id,
            name="Cotton Brokers International",
            partner_type="BROKER",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            created_by=None,
        )
        db.add(bp3)
        print(f"  ✅ Created: {bp3.name} ({bp3.partner_type})")
        
        db.flush()  # Get IDs
        
        # Create Users
        print("\n👤 Creating Users...")
        
        # 1. SUPER_ADMIN
        super_admin = User(
            id=uuid4(),
            user_type="SUPER_ADMIN",
            business_partner_id=None,
            organization_id=None,
            allowed_modules=None,  # Access to all modules
            email="superadmin@rnrl.com",
            full_name="Super Administrator",
            password_hash=pwd_context.hash("Admin123"),
            is_active=True,
        )
        db.add(super_admin)
        print(f"  ✅ Created SUPER_ADMIN: {super_admin.email}")
        print(f"     Password: SuperAdmin@123")
        print(f"     Access: ALL data globally")
        
        # 2. INTERNAL Users (back-office)
        internal1 = User(
            id=uuid4(),
            user_type="INTERNAL",
            business_partner_id=None,
            organization_id=org_id,  # Set organization ID
            allowed_modules=["trade-desk", "invoices", "payments", "quality"],
            email="backoffice1@rnrl.com",
            full_name="Back Office Manager 1",
            password_hash=pwd_context.hash("password123"),
            is_active=True,
        )
        db.add(internal1)
        print(f"  ✅ Created INTERNAL: {internal1.email}")
        print(f"     Password: BackOffice@123")
        print(f"     Access: ALL business partners")
        print(f"     Modules: {', '.join(internal1.allowed_modules)}")
        
        internal2 = User(
            id=uuid4(),
            user_type="INTERNAL",
            business_partner_id=None,
            organization_id=org_id,  # Set organization ID
            allowed_modules=["trade-desk", "contracts"],
            email="backoffice2@rnrl.com",
            full_name="Back Office Manager 2",
            password_hash=pwd_context.hash("password123"),
            is_active=True,
        )
        db.add(internal2)
        print(f"  ✅ Created INTERNAL: {internal2.email}")
        print(f"     Password: BackOffice@123")
        print(f"     Modules: {', '.join(internal2.allowed_modules)}")
        
        # 3. EXTERNAL Users (business partners)
        external1 = User(
            id=uuid4(),
            user_type="EXTERNAL",
            business_partner_id=bp1_id,
            organization_id=None,
            allowed_modules=["trade-desk", "invoices", "contracts"],
            email="buyer@acmetrading.com",
            full_name="John Buyer",
            password_hash=pwd_context.hash("password123"),
            is_active=True,
        )
        db.add(external1)
        print(f"  ✅ Created EXTERNAL: {external1.email}")
        print(f"     Password: Buyer@123")
        print(f"     Business Partner: {bp1.name}")
        print(f"     Access: ONLY data for {bp1.name}")
        print(f"     Modules: {', '.join(external1.allowed_modules)}")
        
        external2 = User(
            id=uuid4(),
            user_type="EXTERNAL",
            business_partner_id=bp2_id,
            organization_id=None,
            allowed_modules=["trade-desk", "quality", "shipments"],
            email="seller@globalcotton.com",
            full_name="Jane Seller",
            password_hash=pwd_context.hash("password123"),
            is_active=True,
        )
        db.add(external2)
        print(f"  ✅ Created EXTERNAL: {external2.email}")
        print(f"     Password: Seller@123")
        print(f"     Business Partner: {bp2.name}")
        print(f"     Access: ONLY data for {bp2.name}")
        print(f"     Modules: {', '.join(external2.allowed_modules)}")
        
        external3 = User(
            id=uuid4(),
            user_type="EXTERNAL",
            business_partner_id=bp3_id,
            organization_id=None,
            allowed_modules=["trade-desk", "contracts", "commissions"],
            email="broker@cottonbrokers.com",
            full_name="Bob Broker",
            password_hash=pwd_context.hash("password123"),
            is_active=True,
        )
        db.add(external3)
        print(f"  ✅ Created EXTERNAL: {external3.email}")
        print(f"     Password: Broker@123")
        print(f"     Business Partner: {bp3.name}")
        print(f"     Access: ONLY data for {bp3.name}")
        print(f"     Modules: {', '.join(external3.allowed_modules)}")
        
        # Commit all
        db.commit()
        
        print("\n✅ Seed data created successfully!")
        print("\n📋 Summary:")
        print(f"  - Business Partners: 3")
        print(f"  - SUPER_ADMIN users: 1")
        print(f"  - INTERNAL users: 2")
        print(f"  - EXTERNAL users: 3")
        print(f"\n🧪 Test Data Isolation:")
        print(f"  1. Login as superadmin@rnrl.com → See ALL data")
        print(f"  2. Login as backoffice1@rnrl.com → See ALL business partners")
        print(f"  3. Login as buyer@acmetrading.com → See ONLY Acme Trading Co. data")
        print(f"  4. Login as seller@globalcotton.com → See ONLY Global Cotton Suppliers data")
        
    except Exception as e:
        print(f"\n❌ Error creating seed data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_seed_data()
