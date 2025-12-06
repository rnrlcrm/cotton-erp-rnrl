#!/usr/bin/env python3
"""
Create Admin User Script
Creates a test admin user for backoffice login
"""

import asyncio
import sys
sys.path.insert(0, '/workspaces/cotton-erp-rnrl/backend')

from sqlalchemy.ext.asyncio import AsyncSession
from backend.modules.settings.services.settings_services import AuthService
from backend.app.database import SessionLocal

async def create_admin():
    """Create admin user with credentials"""
    async with SessionLocal() as db:
        svc = AuthService(db)
        
        # Create admin user
        email = "admin@rnrl.com"
        password = "Admin123"  # Min 8 chars, uppercase, lowercase, number
        full_name = "RNRL Administrator"
        
        try:
            user = await svc.signup(email, password, full_name)
            await db.commit()
            
            print("✅ Admin user created successfully!")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            print(f"   User ID: {user.id}")
            print(f"   Full Name: {user.full_name}")
            print(f"\nYou can now login at: http://localhost:3000/login")
            
        except ValueError as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  User {email} already exists!")
                print(f"   You can login with:")
                print(f"   Email: {email}")
                print(f"   Password: {password}")
            else:
                print(f"❌ Error creating user: {e}")

if __name__ == "__main__":
    asyncio.run(create_admin())
