# EMERGENCY INFRASTRUCTURE FIX - IMPLEMENTATION PLAN

**Status**: 🔴 **CRITICAL** - Multiple modules non-compliant  
**Timeline**: **IMMEDIATE** - No tolerance for delays  
**Scope**: System-wide infrastructure gaps

---

## 🚨 CRITICAL FINDINGS

### Modules Audited:
1. ✅ **availability_routes.py** - COMPLIANT (idempotency added)
2. ✅ **requirement_routes.py** - COMPLIANT (idempotency added)
3. ❌ **auth/router.py** - 1 POST endpoint NO idempotency
4. ❌ **partners/router.py** - 11 POST endpoints NO idempotency
5. ❌ **commodities/router.py** - 28 POST/PUT endpoints NO idempotency
6. ❌ **ALL MODULES** - NO outbox pattern
7. ❌ **ALL MODULES** - NO capability authorization
8. ❌ **ALL MODULES** - NO Pub/Sub DLQ

---

## 📋 IMPLEMENTATION PHASES

### PHASE 1: OUTBOX PATTERN (P0 - HIGHEST PRIORITY)

**Why First**: Prevents data loss, enables transactional event publishing

#### Step 1.1: Create Outbox Table
```sql
-- File: backend/alembic/versions/xxx_create_event_outbox.py

CREATE TABLE event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    event_version INT NOT NULL DEFAULT 1,
    aggregate_type VARCHAR(50) NOT NULL,  -- 'partner', 'availability', etc.
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB,  -- user_id, organization_id, etc.
    
    -- Publishing status
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    retry_count INT DEFAULT 0,
    last_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for efficient polling
    INDEX idx_outbox_unpublished (published, created_at) WHERE NOT published,
    INDEX idx_outbox_aggregate (aggregate_type, aggregate_id),
    INDEX idx_outbox_created (created_at DESC)
);

-- Partition by month for performance
CREATE TABLE event_outbox_2025_11 PARTITION OF event_outbox
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

#### Step 1.2: Create Outbox Model
```python
# File: backend/core/events/outbox.py

from sqlalchemy import Column, String, Boolean, Integer, DateTime, UUID, JSON, text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.base import Base
import uuid

class EventOutbox(Base):
    __tablename__ = "event_outbox"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    event_version = Column(Integer, nullable=False, default=1)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSON, nullable=False)
    metadata = Column(JSON)
    
    published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime(timezone=True))
    retry_count = Column(Integer, default=0, nullable=False)
    last_error = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))
```

#### Step 1.3: Update Event Emitter
```python
# File: backend/core/events/emitter.py (REPLACE direct Pub/Sub)

from backend.core.events.outbox import EventOutbox

class EventEmitter:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def emit(self, event: BaseEvent):
        """
        Write event to outbox table (transactional safety).
        
        Background worker will publish from outbox to Pub/Sub.
        """
        outbox_record = EventOutbox(
            event_type=event.event_type,
            event_version=event.version,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            payload=event.dict(),
            metadata={
                "user_id": event.metadata.get("user_id"),
                "organization_id": event.metadata.get("organization_id"),
                "correlation_id": event.metadata.get("correlation_id")
            }
        )
        
        self.db.add(outbox_record)
        # Will be committed with business transaction ✅
```

#### Step 1.4: Create Outbox Publisher Worker
```python
# File: backend/workers/outbox_publisher.py

import asyncio
from google.cloud import pubsub_v1
from sqlalchemy import select, update
from backend.core.events.outbox import EventOutbox
from backend.db.session import AsyncSessionLocal

class OutboxPublisher:
    """
    Background worker that publishes events from outbox to Pub/Sub.
    
    Runs every 1 second, processes up to 100 unpublished events per batch.
    """
    
    def __init__(self):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(
            "cotton-erp-prod", 
            "domain-events"
        )
    
    async def run_forever(self):
        """Main worker loop"""
        while True:
            try:
                await self.process_batch()
                await asyncio.sleep(1)  # Poll every second
            except Exception as e:
                logger.error(f"Outbox publisher error: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    async def process_batch(self):
        """Process one batch of unpublished events"""
        async with AsyncSessionLocal() as db:
            # Get unpublished events (oldest first)
            result = await db.execute(
                select(EventOutbox)
                .where(EventOutbox.published == False)
                .order_by(EventOutbox.created_at.asc())
                .limit(100)
                .with_for_update(skip_locked=True)  # Lock rows
            )
            events = result.scalars().all()
            
            for event in events:
                try:
                    # Publish to Pub/Sub
                    future = self.publisher.publish(
                        self.topic_path,
                        data=json.dumps(event.payload).encode("utf-8"),
                        event_type=event.event_type,
                        event_version=str(event.event_version),
                        aggregate_id=str(event.aggregate_id)
                    )
                    
                    # Wait for publish (with timeout)
                    message_id = future.result(timeout=10.0)
                    
                    # Mark as published
                    event.published = True
                    event.published_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Published event {event.id} to Pub/Sub: {message_id}")
                    
                except Exception as e:
                    # Increment retry count, log error
                    event.retry_count += 1
                    event.last_error = str(e)
                    
                    # Move to DLQ after 5 retries
                    if event.retry_count >= 5:
                        logger.error(f"Event {event.id} failed 5 times, moving to DLQ")
                        await self.move_to_dlq(event)
                        event.published = True  # Don't retry anymore
                    
                    logger.error(f"Failed to publish event {event.id}: {e}")
            
            await db.commit()

# Run worker
if __name__ == "__main__":
    worker = OutboxPublisher()
    asyncio.run(worker.run_forever())
```

#### Step 1.5: Deploy Worker as Cloud Run Job
```bash
# Dockerfile.outbox-worker
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ backend/
CMD ["python", "-m", "backend.workers.outbox_publisher"]
```

```bash
# Deploy to Cloud Run
gcloud run jobs create outbox-publisher \
  --image gcr.io/cotton-erp-prod/outbox-publisher:latest \
  --region asia-south1 \
  --task-timeout 3600 \
  --max-retries 3 \
  --execute-now  # Run immediately
  --schedule "* * * * *"  # Run every minute as backup
```

---

### PHASE 2: PUB/SUB DLQ + RETRY (P0)

#### Step 2.1: Create DLQ Topic
```python
# File: backend/core/events/pubsub_setup.py

from google.cloud import pubsub_v1

def setup_pubsub():
    """One-time setup for Pub/Sub topics and subscriptions"""
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    
    project_id = "cotton-erp-prod"
    
    # Create DLQ topic
    dlq_topic_path = publisher.topic_path(project_id, "domain-events-dlq")
    try:
        publisher.create_topic(request={"name": dlq_topic_path})
        print(f"✅ Created DLQ topic: {dlq_topic_path}")
    except AlreadyExists:
        print(f"⚠️ DLQ topic already exists")
    
    # Create main topic (if not exists)
    main_topic_path = publisher.topic_path(project_id, "domain-events")
    try:
        publisher.create_topic(request={"name": main_topic_path})
        print(f"✅ Created main topic: {main_topic_path}")
    except AlreadyExists:
        print(f"⚠️ Main topic already exists")
    
    # Create subscription with DLQ
    subscription_path = subscriber.subscription_path(project_id, "domain-events-sub")
    try:
        subscriber.create_subscription(
            request={
                "name": subscription_path,
                "topic": main_topic_path,
                "ack_deadline_seconds": 60,
                "message_retention_duration": {"seconds": 86400 * 7},  # 7 days
                "dead_letter_policy": {
                    "dead_letter_topic": dlq_topic_path,
                    "max_delivery_attempts": 5  # ✅ Retry 5 times before DLQ
                },
                "retry_policy": {
                    "minimum_backoff": {"seconds": 10},    # Start at 10s
                    "maximum_backoff": {"seconds": 600},   # Max 10min
                },
                "enable_exactly_once_delivery": True  # ✅ Idempotent delivery
            }
        )
        print(f"✅ Created subscription with DLQ: {subscription_path}")
    except AlreadyExists:
        print(f"⚠️ Subscription already exists")

# Run setup
if __name__ == "__main__":
    setup_pubsub()
```

#### Step 2.2: Monitor DLQ
```python
# File: backend/monitoring/dlq_monitor.py

import asyncio
from google.cloud import monitoring_v3, pubsub_v1

async def monitor_dlq():
    """Alert if DLQ message count exceeds threshold"""
    subscriber = pubsub_v1.SubscriberClient()
    
    while True:
        try:
            # Get DLQ message count
            subscription_path = subscriber.subscription_path(
                "cotton-erp-prod", 
                "domain-events-dlq-sub"
            )
            
            response = subscriber.get_subscription(
                request={"subscription": subscription_path}
            )
            
            # Check num_undelivered_messages
            message_count = response.num_undelivered_messages
            
            if message_count > 100:
                # ALERT: Too many DLQ messages
                logger.error(f"🚨 DLQ threshold exceeded: {message_count} messages")
                # Send to Slack/PagerDuty
                await send_alert(f"DLQ has {message_count} messages")
            
            logger.info(f"DLQ message count: {message_count}")
            
        except Exception as e:
            logger.error(f"DLQ monitor error: {e}")
        
        await asyncio.sleep(60)  # Check every minute

if __name__ == "__main__":
    asyncio.run(monitor_dlq())
```

---

### PHASE 3: CAPABILITY-BASED AUTHORIZATION (P0)

#### Step 3.1: Define Capabilities
```python
# File: backend/core/auth/capabilities.py

from enum import Enum

class Capability(str, Enum):
    """
    Fine-grained capabilities beyond role-based access.
    
    Format: <resource>:<action>[:<modifier>]
    """
    
    # ========== AVAILABILITY CAPABILITIES ==========
    AVAILABILITY_POST = "availability:post"
    AVAILABILITY_EDIT_OWN = "availability:edit:own"
    AVAILABILITY_EDIT_ANY = "availability:edit:any"
    AVAILABILITY_APPROVE = "availability:approve"
    AVAILABILITY_CANCEL = "availability:cancel"
    AVAILABILITY_VIEW_ALL = "availability:view:all"  # Internal only
    
    # ========== REQUIREMENT CAPABILITIES ==========
    REQUIREMENT_POST = "requirement:post"
    REQUIREMENT_EDIT_OWN = "requirement:edit:own"
    REQUIREMENT_EDIT_ANY = "requirement:edit:any"
    REQUIREMENT_CANCEL = "requirement:cancel"
    REQUIREMENT_VIEW_ALL = "requirement:view:all"  # Internal only
    
    # ========== TRADE CAPABILITIES ==========
    TRADE_INITIATE = "trade:initiate"
    TRADE_APPROVE = "trade:approve"
    TRADE_APPROVE_HIGH_VALUE = "trade:approve:high_value"  # > ₹1Cr
    TRADE_SETTLE = "trade:settle"
    TRADE_CANCEL = "trade:cancel"
    TRADE_VIEW_ALL = "trade:view:all"  # Internal only
    
    # ========== PARTNER CAPABILITIES ==========
    PARTNER_ONBOARD = "partner:onboard"
    PARTNER_APPROVE = "partner:approve"
    PARTNER_VERIFY_KYC = "partner:kyc:verify"
    PARTNER_EDIT = "partner:edit"
    PARTNER_SUSPEND = "partner:suspend"
    
    # ========== SETTINGS CAPABILITIES ==========
    COMMODITY_MANAGE = "commodity:manage"
    LOCATION_MANAGE = "location:manage"
    ORGANIZATION_MANAGE = "organization:manage"
    
    # ========== ADMIN CAPABILITIES ==========
    ADMIN_ALL = "admin:all"  # Super admin
```

#### Step 3.2: Create Capability Database
```sql
-- File: alembic/versions/xxx_create_capabilities.py

CREATE TABLE capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'availability:post'
    description TEXT,
    resource_type VARCHAR(50),  -- 'availability', 'trade', etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE role_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID REFERENCES roles(id),
    capability_id UUID REFERENCES capabilities(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(role_id, capability_id)
);

CREATE TABLE user_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    capability_id UUID REFERENCES capabilities(id),
    organization_id UUID REFERENCES organizations(id),  -- Org-specific
    expires_at TIMESTAMPTZ,  -- Temporary capabilities
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, capability_id, organization_id)
);

-- Indexes
CREATE INDEX idx_role_capabilities ON role_capabilities(role_id);
CREATE INDEX idx_user_capabilities ON user_capabilities(user_id);
```

#### Step 3.3: Capability Service
```python
# File: backend/core/auth/capability_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.auth.capabilities import Capability

class CapabilityService:
    """Check user capabilities"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def has_capability(
        self, 
        user_id: UUID, 
        capability: Capability,
        organization_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if user has capability.
        
        Checks:
        1. User-specific capabilities
        2. Role-based capabilities
        3. Super admin override
        """
        # Check super admin (has all capabilities)
        if await self.is_super_admin(user_id):
            return True
        
        # Check user-specific capabilities
        result = await self.db.execute(
            select(UserCapability)
            .join(Capability)
            .where(
                UserCapability.user_id == user_id,
                Capability.name == capability.value,
                (UserCapability.organization_id == organization_id) | 
                (UserCapability.organization_id.is_(None)),
                (UserCapability.expires_at.is_(None)) |
                (UserCapability.expires_at > datetime.now(timezone.utc))
            )
        )
        if result.scalar_one_or_none():
            return True
        
        # Check role-based capabilities
        result = await self.db.execute(
            select(RoleCapability)
            .join(Capability)
            .join(UserRole)
            .where(
                UserRole.user_id == user_id,
                Capability.name == capability.value
            )
        )
        if result.scalar_one_or_none():
            return True
        
        return False
    
    async def require_capability(
        self, 
        user_id: UUID, 
        capability: Capability,
        organization_id: Optional[UUID] = None
    ):
        """Raise HTTPException if user lacks capability"""
        if not await self.has_capability(user_id, capability, organization_id):
            raise HTTPException(
                status_code=403,
                detail=f"Missing capability: {capability.value}"
            )
```

#### Step 3.4: Use in Services
```python
# File: backend/modules/trade_desk/services/availability_service.py

from backend.core.auth.capabilities import Capability
from backend.core.auth.capability_service import CapabilityService

class AvailabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.capability_service = CapabilityService(db)
    
    async def create_availability(
        self, 
        request: AvailabilityCreateRequest,
        user_id: UUID,
        organization_id: UUID
    ):
        # ✅ CHECK CAPABILITY
        await self.capability_service.require_capability(
            user_id, 
            Capability.AVAILABILITY_POST,
            organization_id
        )
        
        # Business logic...
        availability = Availability(...)
        self.db.add(availability)
        
        # Emit event to OUTBOX
        event = AvailabilityCreatedEvent(availability_id=availability.id)
        await self.event_emitter.emit(event)  # Goes to outbox
        
        await self.db.commit()  # ✅ Transactional safety
        
        return availability
```

---

### PHASE 4: ADD IDEMPOTENCY TO ALL POST/PUT ENDPOINTS (P1)

**Target**: 40+ endpoints across all modules

#### Batch Fix Script
```python
# File: scripts/add_idempotency_headers.py

import re
from pathlib import Path

def add_idempotency_to_router(filepath: Path):
    """Auto-add idempotency header to all POST/PUT endpoints"""
    
    content = filepath.read_text()
    
    # Find all @router.post and @router.put
    pattern = r'(@router\.(post|put|patch).*?)\nasync def (\w+)\((.*?)\):'
    
    def replace_func(match):
        decorator = match.group(1)
        method = match.group(2)
        func_name = match.group(3)
        params = match.group(4)
        
        # Check if already has idempotency_key
        if 'idempotency_key' in params or 'Idempotency-Key' in params:
            return match.group(0)  # Skip
        
        # Add idempotency_key parameter
        new_params = params.rstrip(',') + ',\n    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")'
        
        return f'{decorator}\nasync def {func_name}({new_params}):'
    
    new_content = re.sub(pattern, replace_func, content, flags=re.DOTALL)
    
    # Add import if not exists
    if 'from typing import Optional' not in new_content:
        new_content = 'from typing import Optional\n' + new_content
    if 'from fastapi import Header' not in new_content:
        new_content = new_content.replace(
            'from fastapi import',
            'from fastapi import Header,'
        )
    
    filepath.write_text(new_content)
    print(f"✅ Updated {filepath}")

# Run on all routers
routers = [
    "backend/modules/auth/router.py",
    "backend/modules/partners/router.py",
    "backend/modules/settings/commodities/router.py",
    # ... all others
]

for router_path in routers:
    add_idempotency_to_router(Path(router_path))
```

---

## 📊 IMPLEMENTATION TIMELINE

| Phase | Tasks | Priority | Duration | Status |
|-------|-------|----------|----------|--------|
| **Phase 1** | Outbox Pattern | P0 | 4 hours | 🔴 NOT STARTED |
| **Phase 2** | Pub/Sub DLQ | P0 | 2 hours | 🔴 NOT STARTED |
| **Phase 3** | Capability Auth | P0 | 6 hours | 🔴 NOT STARTED |
| **Phase 4** | Idempotency | P1 | 3 hours | 🔴 NOT STARTED |

**Total**: 15 hours of focused implementation

---

## ✅ ACCEPTANCE CRITERIA

Before merge to main:

- [ ] Outbox table created and migrated
- [ ] Outbox publisher worker deployed to Cloud Run
- [ ] All event emitters use outbox (not direct Pub/Sub)
- [ ] Pub/Sub DLQ topic created
- [ ] Pub/Sub retry policy configured (5 attempts, exponential backoff)
- [ ] DLQ monitoring deployed
- [ ] Capability enum defined (40+ capabilities)
- [ ] Capability tables created
- [ ] CapabilityService implemented
- [ ] All services check capabilities (not just roles)
- [ ] ALL POST/PUT/PATCH endpoints have idempotency header
- [ ] Infrastructure tests pass
- [ ] E2E tests pass

---

## 🚀 EXECUTION ORDER

1. **NOW**: Create outbox pattern (most critical - prevents data loss)
2. **NEXT**: Configure Pub/Sub DLQ (event delivery guarantee)
3. **THEN**: Implement capability framework (security)
4. **FINALLY**: Add idempotency headers (UX improvement)

---

**START TIME**: NOW  
**END TIME**: 15 hours from now  
**NO EXCUSES. NO DELAYS.**
