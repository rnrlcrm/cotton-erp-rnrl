#!/usr/bin/env python3
"""
Direct Database Admin User Creator
Creates admin user directly in PostgreSQL database
"""

import asyncio
import asyncpg
from passlib.context import CryptContext
from uuid import uuid4
from datetime import datetime

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin_user():
    """Create admin user directly in database"""
    
    # Database connection
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='commodity_user',
        password='commodity_password',
        database='commodity_erp'
    )
    
    try:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            'admin@rnrl.com'
        )
        
        if existing:
            print("✅ Admin user already exists!")
            print(f"   Email: admin@rnrl.com")
            print(f"   User ID: {existing['id']}")
            print("\n🔐 Login at: http://localhost:3000/login")
            print("   Email:    admin@rnrl.com")
            print("   Password: Admin123")
            return
        
        # Hash password
        hashed_password = pwd_context.hash("Admin123")
        user_id = uuid4()
        org_id = uuid4()
        
        # Insert user
        await conn.execute("""
            INSERT INTO users (
                id, email, hashed_password, full_name,
                user_type, role, is_active, organization_id,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            user_id, 'admin@rnrl.com', hashed_password, 'RNRL Administrator',
            'INTERNAL', 'admin', True, org_id,
            datetime.utcnow(), datetime.utcnow()
        )
        
        print("✅ Admin user created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Email: admin@rnrl.com")
        print(f"   Name: RNRL Administrator")
        print("\n🔐 Login Credentials:")
        print("   Email:    admin@rnrl.com")
        print("   Password: Admin123")
        print("\n🌐 Login at: http://localhost:3000/login")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_admin_user())
