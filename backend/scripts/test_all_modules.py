#!/usr/bin/env python3
"""
Manual Test Script for Data Isolation

Tests the complete system after Phase 1 merge to main:
1. Database connectivity
2. Seed data verification
3. All module endpoints accessibility
4. Data isolation middleware integration

Run: python backend/scripts/test_all_modules.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from backend.db.session_module import SessionLocal
from backend.modules.partners.models import BusinessPartner
from backend.modules.settings.models.settings_models import User
from backend.modules.settings.organization.models import Organization


def test_database_connection():
    """Test database connectivity"""
    print("\n🔗 Testing Database Connection...")
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).scalar()
        db.close()
        assert result == 1
        print("  ✅ Database connection successful")
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False


def test_migrations_applied():
    """Test that all migrations are applied"""
    print("\n📊 Testing Migrations...")
    try:
        db = SessionLocal()
        
        # Check business_partners table exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'business_partners'
            )
        """)).scalar()
        assert result is True
        print("  ✅ business_partners table exists")
        
        # Check users table has new columns
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'user_type'
            )
        """)).scalar()
        assert result is True
        print("  ✅ users.user_type column exists")
        
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'business_partner_id'
            )
        """)).scalar()
        assert result is True
        print("  ✅ users.business_partner_id column exists")
        
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'allowed_modules'
            )
        """)).scalar()
        assert result is True
        print("  ✅ users.allowed_modules column exists")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Migration check failed: {e}")
        return False


def test_seed_data():
    """Test that seed data was created"""
    print("\n🌱 Testing Seed Data...")
    try:
        db = SessionLocal()
        
        # Check organizations
        org_count = db.query(Organization).count()
        print(f"  ✅ Organizations: {org_count}")
        
        # Check business partners
        bp_count = db.query(BusinessPartner).count()
        print(f"  ✅ Business Partners: {bp_count}")
        
        # Check users by type
        super_admin_count = db.query(User).filter(User.user_type == "SUPER_ADMIN").count()
        internal_count = db.query(User).filter(User.user_type == "INTERNAL").count()
        external_count = db.query(User).filter(User.user_type == "EXTERNAL").count()
        
        print(f"  ✅ SUPER_ADMIN users: {super_admin_count}")
        print(f"  ✅ INTERNAL users: {internal_count}")
        print(f"  ✅ EXTERNAL users: {external_count}")
        
        # List all users
        print("\n  📋 User Accounts:")
        users = db.query(User).all()
        for user in users:
            bp_name = ""
            if user.business_partner_id:
                bp = db.query(BusinessPartner).filter(
                    BusinessPartner.id == user.business_partner_id
                ).first()
                bp_name = f" ({bp.name})" if bp else ""
            
            print(f"    - {user.email:30} {user.user_type:12} {bp_name}")
        
        db.close()
        return org_count > 0 and bp_count > 0 and (super_admin_count + internal_count + external_count) > 0
        
    except Exception as e:
        print(f"  ❌ Seed data check failed: {e}")
        return False


def test_modules_available():
    """Test that all module files exist"""
    print("\n📦 Testing Module Availability...")
    
    modules = {
        "Settings": "backend/modules/settings/router.py",
        "Organizations": "backend/modules/settings/organization/router.py",
        "Commodities": "backend/modules/settings/commodities/router.py",
        "Locations": "backend/modules/settings/locations/router.py",
        "Business Partners": "backend/modules/settings/business_partners/models.py",
    }
    
    all_exist = True
    for name, path in modules.items():
        full_path = Path(__file__).resolve().parents[1] / path.replace("backend/", "")
        if full_path.exists():
            print(f"  ✅ {name:20} - {path}")
        else:
            print(f"  ❌ {name:20} - NOT FOUND: {path}")
            all_exist = False
    
    return all_exist


def test_middleware_integration():
    """Test that middleware is integrated in main.py"""
    print("\n🔧 Testing Middleware Integration...")
    
    main_file = Path(__file__).resolve().parents[1] / "app" / "main.py"
    content = main_file.read_text()
    
    checks = {
        "AuthMiddleware imported": "from backend.app.middleware import AuthMiddleware",
        "DataIsolationMiddleware imported": "DataIsolationMiddleware",
        "AuthMiddleware added": "app.add_middleware(AuthMiddleware)",
        "DataIsolationMiddleware added": "app.add_middleware(DataIsolationMiddleware)",
    }
    
    all_present = True
    for name, pattern in checks.items():
        if pattern in content:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} - NOT FOUND")
            all_present = False
    
    return all_present


def test_isolation_components():
    """Test that all isolation components exist"""
    print("\n🛡️  Testing Data Isolation Components...")
    
    components = {
        "Security Context": "backend/core/security/context.py",
        "Auth Middleware": "backend/app/middleware/auth.py",
        "Isolation Middleware": "backend/app/middleware/isolation.py",
        "Base Repository": "backend/domain/repositories/base.py",
        "Enhanced Audit Logger": "backend/core/audit/logger.py",
    }
    
    all_exist = True
    for name, path in components.items():
        full_path = Path(__file__).resolve().parents[1] / path.replace("backend/", "")
        if full_path.exists():
            lines = len(full_path.read_text().split('\n'))
            print(f"  ✅ {name:25} - {lines:4} lines")
        else:
            print(f"  ❌ {name:25} - NOT FOUND")
            all_exist = False
    
    return all_exist


def main():
    """Run all tests"""
    print("=" * 70)
    print("🧪 TESTING ALL MODULES AFTER PHASE 1 MERGE TO MAIN")
    print("=" * 70)
    
    results = {
        "Database Connection": test_database_connection(),
        "Migrations Applied": test_migrations_applied(),
        "Seed Data": test_seed_data(),
        "Modules Available": test_modules_available(),
        "Middleware Integration": test_middleware_integration(),
        "Isolation Components": test_isolation_components(),
    }
    
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status:8} - {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print("\n" + "=" * 70)
    print(f"📈 RESULTS: {passed_tests}/{total_tests} tests passed")
    print("=" * 70)
    
    if all(results.values()):
        print("\n✅ ALL TESTS PASSED - System is ready!")
        print("\n🚀 Next Steps:")
        print("  1. Start backend: cd backend && uvicorn backend.app.main:app --reload")
        print("  2. Test login: POST /api/v1/auth/login")
        print("  3. Access modules with JWT token")
        print("  4. Verify data isolation works")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
