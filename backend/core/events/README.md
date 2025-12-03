# Event Sourcing System

## Overview

The event sourcing system provides an **immutable audit trail** for all business operations across all modules. Every state change in the system is captured as an event in the `events` table.

## Architecture

```
┌─────────────────┐
│   Module        │
│   Service       │  1. Perform business logic
│                 │  2. Emit domain event
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  EventEmitter   │  Validates and stores event
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   EventStore    │  Persists to events table (JSONB)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │  Single events table for ALL modules
│  events table   │  Indexed for fast queries
└─────────────────┘
```

## Core Components

### 1. BaseEvent (`base.py`)
- **Immutable** event base class
- All events inherit from this
- Contains: `event_id`, `event_type`, `aggregate_id`, `aggregate_type`, `user_id`, `timestamp`, `data`, `metadata`

### 2. EventStore (`store.py`)
- Repository for storing/retrieving events
- Methods:
  - `append()` - Store new event
  - `get_by_aggregate()` - Get all events for an entity
  - `get_by_type()` - Get events by type
  - `get_by_user()` - Get user activity
  - `get_by_time_range()` - Time-based queries

### 3. EventEmitter (`emitter.py`)
- Service for emitting events from business logic
- Used in all module services
- Single method: `emit(event)` and `emit_many(events)`

### 4. AuditService (`audit.py`)
- High-level audit queries
- Methods:
  - `get_entity_history()` - Complete change history
  - `get_user_activity()` - What a user did
  - `get_recent_changes()` - Recent activity
  - `get_change_count()` - Number of changes

## Database Schema

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,      -- e.g., "organization.created"
    aggregate_id UUID NOT NULL,            -- ID of the entity
    aggregate_type VARCHAR(50) NOT NULL,   -- Type: "organization", "commodity", etc.
    user_id UUID NOT NULL,                 -- Who triggered the event
    timestamp TIMESTAMPTZ NOT NULL,        -- When it happened
    version INTEGER NOT NULL,              -- Event schema version
    data JSONB NOT NULL,                   -- Event payload (flexible)
    metadata JSONB,                        -- Context (IP, user agent, etc.)
    created_at TIMESTAMPTZ NOT NULL
);

-- Indexes for common queries
CREATE INDEX ON events(event_type);
CREATE INDEX ON events(aggregate_id);
CREATE INDEX ON events(aggregate_type);
CREATE INDEX ON events(user_id);
CREATE INDEX ON events(timestamp);
CREATE INDEX ON events(aggregate_id, aggregate_type, timestamp);
```

## Usage in Modules

### Step 1: Define Module Events

Create `events.py` in your module:

```python
from backend.core.events.base import BaseEvent, EventMetadata
import uuid
from typing import Dict, Any, Optional

class CommodityCreated(BaseEvent):
    """Emitted when a new commodity is created"""
    
    def __init__(
        self,
        aggregate_id: uuid.UUID,
        user_id: uuid.UUID,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
    ):
        super().__init__(
            event_type="commodity.created",
            aggregate_id=aggregate_id,
            aggregate_type="commodity",
            user_id=user_id,
            data=data,
            metadata=metadata,
        )
```

### Step 2: Emit Events in Service

```python
from backend.core.events.emitter import EventEmitter
from .events import CommodityCreated

class CommodityService:
    def __init__(self, db: AsyncSession, current_user_id: UUID):
        self.db = db
        self.current_user_id = current_user_id
        self.events = EventEmitter(db)
    
    async def create_commodity(self, data: CommodityCreate):
        # 1. Create entity
        commodity = await self.repo.create(**data.model_dump())
        await self.db.flush()
        
        # 2. Emit event
        await self.events.emit(
            CommodityCreated(
                aggregate_id=commodity.id,
                user_id=self.current_user_id,
                data={
                    "name": commodity.name,
                    "category": commodity.category,
                    "hsn_code": commodity.hsn_code,
                },
            )
        )
        
        # 3. Commit
        await self.db.commit()
        return commodity
```

### Step 3: Query Audit Trail

```python
from backend.core.events.audit import AuditService

audit = AuditService(session)

# Get complete history of an entity
history = await audit.get_entity_history(
    entity_id=commodity_id,
    entity_type="commodity"
)

# Get user activity
activity = await audit.get_user_activity(
    user_id=user_id,
    limit=50
)

# Get recent changes
recent = await audit.get_recent_changes(
    entity_type="commodity",
    hours=24
)
```

## Event Naming Convention

Format: `{aggregate_type}.{action}`

Examples:
- `organization.created`
- `organization.updated`
- `organization.gst.added`
- `commodity.created`
- `trade.executed`
- `payment.received`

## Event Data Structure

### For CREATE events:
```json
{
  "name": "Commodity Trading Ltd",
  "type": "corporation",
  "email": "contact@commoditytrading.com"
}
```

### For UPDATE events:
```json
{
  "changes": {
    "email": {
      "old": "old@example.com",
      "new": "new@example.com"
    },
    "phone": {
      "old": "+91-1234567890",
      "new": "+91-9876543210"
    }
  }
}
```

### For DELETE events:
```json
{
  "name": "Entity Name",
  "deleted_at": "2025-11-21T10:30:00Z"
}
```

## Metadata

Optional context about the event:

```python
metadata = EventMetadata(
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    reason="Updated as per compliance review",
    correlation_id="trade-123-update"  # Link related events
)
```

## Benefits

### 1. Complete Audit Trail
- Every change is recorded
- Who did what, when
- Full history reconstruction

### 2. Compliance
- Meet regulatory requirements
- Dispute resolution
- Forensic analysis

### 3. Debugging
- Understand system behavior
- Trace bugs through history
- Replay events to reproduce issues

### 4. Future Features
- Event replay for testing
- Real-time notifications
- Analytics and reporting
- Event-driven workflows

## Performance

- **Single write per operation**: Event stored in same transaction
- **JSONB indexing**: Fast queries on event data
- **Composite indexes**: Optimized for common query patterns
- **No impact on reads**: Events don't slow down normal queries

## Migration Path

1. ✅ **Core system built** - `backend/core/events/`
2. ✅ **Events table created** - Migration applied
3. ✅ **Organization module retrofitted** - First module with events
4. ⏳ **All new modules** - Will have events from day 1
5. ⏳ **Audit UI** - Timeline view of changes
6. ⏳ **Real-time notifications** - Webhooks/SSE for events

## Example: Organization Module

See `backend/modules/settings/organization/events.py` for event definitions.

Key events:
- `organization.created`
- `organization.updated`
- `organization.deleted`
- `organization.gst.added`
- `organization.gst.updated`
- `organization.bank_account.added`
- `organization.bank_account.updated`
- `organization.financial_year.added`
- `organization.document_series.added`

All emitted from `services.py` methods.
