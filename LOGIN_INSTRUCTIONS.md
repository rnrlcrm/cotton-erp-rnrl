# 🔐 How to Login to the Backoffice

## Quick Start - Create Admin User

You have **3 options** to create an admin user:

### Option 1: Use the Makefile (Easiest)
```bash
cd /workspaces/cotton-erp-rnrl
make create-admin-user
```

### Option 2: Start Backend & Use API
```bash
# Terminal 1: Start backend
cd /workspaces/cotton-erp-rnrl/backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Create user via API
curl -X POST http://localhost:8000/api/v1/settings/auth/signup-internal \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@rnrl.com",
    "password": "Admin123",
    "full_name": "RNRL Administrator"
  }'
```

### Option 3: Use Python Script
```bash
cd /workspaces/cotton-erp-rnrl/backend
export DATABASE_URL="postgresql+asyncpg://commodity_user:commodity_password@localhost:5432/commodity_erp"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="your-secret-key-change-in-production"
python create_admin_user.py
```

## Login Credentials

Once created, use these credentials at http://localhost:3000/login:

```
Email: admin@rnrl.com
Password: Admin123
```

**Password Requirements:**
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter  
- At least 1 number

## Services Status

Make sure these services are running:

✅ **Database & Redis:**
```bash
cd /workspaces/cotton-erp-rnrl
docker-compose up -d postgres redis
```

✅ **Backend API:**
```bash
cd /workspaces/cotton-erp-rnrl/backend
uvicorn app.main:app --reload --port 8000
```

✅ **Frontend:**
```bash
cd /workspaces/cotton-erp-rnrl/frontend
npm run dev
```

## Verify Everything Works

1. **Check backend health:** http://localhost:8000/docs
2. **Check frontend:** http://localhost:3000/login
3. **Login** with admin@rnrl.com / Admin123
4. **You should be redirected** to /backoffice dashboard

## Troubleshooting

**"Network Error" on login:**
- Backend not running → Start with `uvicorn app.main:app --reload --port 8000`

**"Invalid credentials":**
- User not created → Use one of the 3 options above
- Wrong password → Must be exactly "Admin123"

**"Database connection error":**
- PostgreSQL not running → Run `docker-compose up -d postgres redis`
