#!/usr/bin/env python3
"""
Quick Admin User Creator
Run this after backend is started to create admin login
"""

import requests
import time
import sys

def create_admin():
    """Create admin user via API"""
    
    # Wait for backend to be ready
    print("⏳ Waiting for backend to start...")
    for i in range(10):
        try:
            response = requests.get("http://localhost:8000/docs", timeout=2)
            if response.status_code == 200:
                print("✅ Backend is ready!")
                break
        except:
            time.sleep(1)
            print(f"   Attempt {i+1}/10...")
    else:
        print("❌ Backend not responding. Make sure it's running on port 8000")
        sys.exit(1)
    
    # Create admin user
    print("\n📝 Creating admin user...")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/settings/auth/signup-internal",
            json={
                "email": "admin@rnrl.com",
                "password": "Admin123",
                "full_name": "RNRL Administrator"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            user = response.json()
            print("\n✅ Admin user created successfully!")
            print(f"   User ID: {user.get('id')}")
            print(f"   Name: {user.get('full_name')}")
            print(f"   Email: {user.get('email')}")
            print("\n🔐 Login Credentials:")
            print("   Email:    admin@rnrl.com")
            print("   Password: Admin123")
            print("\n🌐 Login at: http://localhost:3000/login")
            
        elif response.status_code == 400 and "already exists" in response.text.lower():
            print("\nℹ️  Admin user already exists!")
            print("\n🔐 Login Credentials:")
            print("   Email:    admin@rnrl.com")
            print("   Password: Admin123")
            print("\n🌐 Login at: http://localhost:3000/login")
            
        else:
            print(f"\n❌ Error creating user:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_admin()
