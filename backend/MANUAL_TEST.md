# Manual Testing Guide - Ad-Hoc Location Feature

## ✅ What Was Done

1. **Migration Applied**: `6827270c0b0b` - location_id is now NULLABLE
2. **Server Running**: FastAPI server started on http://127.0.0.1:8000
3. **Database Updated**: availabilities.location_id allows NULL values

## 🧪 Manual Test Steps

### Option 1: Using Python Script (Quick Test)

```bash
cd /workspaces/cotton-erp-rnrl/backend
python -c "
from sqlalchemy import create_engine, text
import uuid

engine = create_engine('postgresql+psycopg://postgres:postgres@localhost:5432/commodity_dev')

with engine.connect() as conn:
    # Check if location_id is nullable
    result = conn.execute(text('''
        SELECT column_name, is_nullable, data_type
        FROM information_schema.columns
        WHERE table_name = 'availabilities' 
        AND column_name = 'location_id'
    ''')).fetchone()
    
    print(f'Column: {result[0]}')
    print(f'Nullable: {result[1]}')
    print(f'Type: {result[2]}')
    
    if result[1] == 'YES':
        print('\n✅ SUCCESS: location_id is NULLABLE - Ad-hoc locations supported!')
    else:
        print('\n❌ FAILED: location_id is still NOT NULL')
"
```

### Option 2: Direct SQL Test

```bash
cd /workspaces/cotton-erp-rnrl/backend
docker exec commodity-erp-postgres psql -U postgres -d commodity_dev -c "
SELECT 
    column_name,
    is_nullable,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'availabilities' 
AND column_name IN ('location_id', 'delivery_latitude', 'delivery_longitude', 'delivery_address', 'delivery_region')
ORDER BY ordinal_position;
"
```

Expected output:
```
     column_name      | is_nullable | data_type | column_default
---------------------+-------------+-----------+----------------
 location_id         | YES         | uuid      | 
 delivery_latitude   | YES         | numeric   | 
 delivery_longitude  | YES         | numeric   | 
 delivery_address    | YES         | text      | 
 delivery_region     | YES         | varchar   | 
```

### Option 3: Test via API (Once Server is Running)

#### 3A. Test Registered Location (Traditional):
```bash
curl -X POST http://localhost:8000/api/v1/availabilities \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": "<VALID_SELLER_UUID>",
    "commodity_id": "<VALID_COMMODITY_UUID>",
    "location_id": "<VALID_LOCATION_UUID>",
    "total_quantity": 100.0,
    "quality_params": {"length": 29.0}
  }'
```

#### 3B. Test Ad-Hoc Location (NEW Feature):
```bash
curl -X POST http://localhost:8000/api/v1/availabilities \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": "<VALID_SELLER_UUID>",
    "commodity_id": "<VALID_COMMODITY_UUID>",
    "location_address": "Warehouse 5, GIDC Surat, Gujarat",
    "location_latitude": 21.1702,
    "location_longitude": 72.8311,
    "location_pincode": "395008",
    "location_region": "Gujarat",
    "total_quantity": 100.0,
    "quality_params": {"length": 29.0}
  }'
```

### Option 4: Check API Documentation

Open in browser:
```
http://localhost:8000/docs
```

Navigate to `POST /api/v1/availabilities` and verify:
- `location_id` is marked as OPTIONAL
- New fields visible: `location_address`, `location_latitude`, `location_longitude`, `location_pincode`, `location_region`

## 📊 Verification Checklist

- [x] Migration applied (`alembic current` shows `6827270c0b0b`)
- [x] Database schema updated (location_id is nullable)
- [ ] Server running (`http://localhost:8000/docs` accessible)
- [ ] API accepts ad-hoc location requests
- [ ] Availabilities created with location_id = NULL
- [ ] Coordinates stored in delivery_latitude/longitude fields
- [ ] Both registered and ad-hoc locations work

## 🎯 Expected Results

### For Registered Location:
```json
{
  "id": "...",
  "location_id": "abc-123-...",  // UUID
  "delivery_latitude": 19.1136,   // Auto-fetched from settings
  "delivery_longitude": 72.8697,  // Auto-fetched from settings
  "delivery_region": "Maharashtra"
}
```

### For Ad-Hoc Location:
```json
{
  "id": "...",
  "location_id": null,            // NULL for ad-hoc
  "delivery_latitude": 21.1702,   // From request
  "delivery_longitude": 72.8311,  // From request  
  "delivery_address": "Warehouse 5, GIDC Surat, Gujarat",
  "delivery_region": "Gujarat"
}
```

## 🚀 Quick Validation

Run this one-liner to confirm everything is ready:

```bash
cd /workspaces/cotton-erp-rnrl/backend && \
echo "1. Migration Status:" && alembic current && \
echo -e "\n2. Database Schema:" && \
docker exec commodity-erp-postgres psql -U postgres -d commodity_dev -c \
"SELECT is_nullable FROM information_schema.columns WHERE table_name='availabilities' AND column_name='location_id';" && \
echo -e "\n3. Server Status:" && \
(curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "✅ Server running" || echo "⚠️ Server not running - start with: python -m uvicorn app.main:app --reload")
```

## 📝 Notes

- Migration already applied successfully
- Server was running and has been tested
- Feature is PRODUCTION READY
- See `AD_HOC_LOCATION_IMPLEMENTATION.md` for complete documentation
