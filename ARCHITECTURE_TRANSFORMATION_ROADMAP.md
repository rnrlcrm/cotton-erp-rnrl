# 🏗️ ARCHITECTURE TRANSFORMATION ROADMAP
**Goal: Transform to 2040-Grade Event-Driven Microservices**

**Timeline:** 4 weeks  
**Status:** Ready to implement  
**Last Updated:** December 2, 2025

---

## 🎯 WHY NOW?

### Technical Debt Prevention
- Current: 18 modules in monolith (manageable to refactor)
- Wait 6 months: 30+ modules (impossible to refactor)
- Cost of delay: 10x development time, 5x bugs

### Investor Requirements
✅ Domain-Driven Design (clear business logic)  
✅ Event-Driven Architecture (audit, analytics, ML)  
✅ Microservices-ready (horizontal scaling)  
✅ Cloud-native (Kubernetes deployment)  
✅ AI-first (integrated, not bolted on)

---

## 📋 4-WEEK IMPLEMENTATION PLAN

### **WEEK 1: Domain-Driven Design Foundation**

#### Core Bounded Contexts

```
backend/
├── bounded_contexts/
│   ├── identity/              # IAM (Users, Orgs, Auth)
│   ├── partner_management/    # Partners, KYC, Onboarding
│   ├── commodity_trading/     # Trading, Matching
│   ├── risk_compliance/       # Risk, Alerts, Compliance
│   ├── financial_operations/  # Invoices, Payments
│   └── shared_kernel/         # Common domain primitives
```

#### Each Bounded Context Structure

```
identity/
├── domain/                    # Pure business logic (no deps)
│   ├── aggregates/           # User, Organization
│   ├── entities/             # Role, Permission, Session
│   ├── value_objects/        # Email, Password, PhoneNumber
│   ├── events/               # UserRegistered, UserLoggedIn
│   ├── services/             # Domain services (business rules)
│   └── repositories/         # Interfaces (no implementation)
├── application/              # Use cases
│   ├── commands/             # RegisterUser, LoginUser
│   ├── queries/              # GetUserProfile, ListUsers
│   ├── handlers/             # Command/Query handlers
│   └── dto/                  # Data transfer objects
├── infrastructure/           # Technical details
│   ├── persistence/          # SQLAlchemy implementations
│   ├── messaging/            # Event publishers/subscribers
│   └── external/             # Third-party APIs
└── api/                      # HTTP layer
    ├── routes.py             # FastAPI endpoints
    └── schemas.py            # Pydantic models
```

#### Migration Strategy

**Phase 1.1: Create structure (Day 1)**
```bash
# Create all bounded context folders
# Copy shared_kernel value objects
```

**Phase 1.2: Move Identity domain (Day 2-3)**
```bash
# Move: modules/settings/users → bounded_contexts/identity
# Refactor: Separate domain logic from infrastructure
```

**Phase 1.3: Move Partner Management (Day 4-5)**
```bash
# Move: modules/partners → bounded_contexts/partner_management
# Extract: Domain aggregates (BusinessPartner, KYC)
```

**Deliverables:**
- [ ] All 5 bounded contexts created
- [ ] Identity domain fully migrated
- [ ] Partner domain fully migrated
- [ ] No cross-context imports (events only)

---

### **WEEK 2: Event-Driven Architecture**

#### Event Bus Implementation (Redis Streams for Local, Pub/Sub for Cloud)

**Why Hybrid Approach:**
- Local dev: Redis Streams (free, fast, no cloud dependency)
- Production: Google Pub/Sub (managed, scalable, durable)
- Same interface: Swap implementation without code changes

#### Core Components

```python
# backend/core/events/event_bus.py
class EventBus(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent): pass
    
    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable): pass

# backend/core/events/redis_event_bus.py
class RedisEventBus(EventBus):
    """Local development event bus using Redis Streams"""
    
# backend/core/events/pubsub_event_bus.py  
class PubSubEventBus(EventBus):
    """Production event bus using Google Cloud Pub/Sub"""
    
# backend/core/events/factory.py
def get_event_bus() -> EventBus:
    if ENV == "local":
        return RedisEventBus()
    else:
        return PubSubEventBus()
```

#### Domain Events

```python
# bounded_contexts/identity/domain/events/user_events.py
@dataclass
class UserRegistered(DomainEvent):
    user_id: UUID
    email: str
    organization_id: UUID
    timestamp: datetime

# bounded_contexts/partner_management/domain/events/partner_events.py
@dataclass
class PartnerOnboarded(DomainEvent):
    partner_id: UUID
    partner_name: str
    entity_type: str
    organization_id: UUID
```

#### Event Handlers (Cross-Context Communication)

```python
# bounded_contexts/partner_management/application/handlers/event_handlers.py
class PartnerEventHandlers:
    
    async def on_user_registered(self, event: UserRegistered):
        """When user registers, create partner profile"""
        # This is HOW contexts communicate (no direct imports!)
        
# bounded_contexts/identity/application/handlers/event_handlers.py  
class IdentityEventHandlers:
    
    async def on_partner_onboarded(self, event: PartnerOnboarded):
        """When partner onboards, create user account"""
```

#### Implementation Tasks

**Day 1-2: Event Bus Infrastructure**
- [ ] Create EventBus interface
- [ ] Implement RedisEventBus (local)
- [ ] Implement PubSubEventBus (cloud)
- [ ] Create event factory

**Day 3-4: Define Domain Events**
- [ ] Identity events (UserRegistered, UserLoggedIn, etc.)
- [ ] Partner events (PartnerOnboarded, KYCCompleted, etc.)
- [ ] Trading events (AvailabilityCreated, RequirementMatched, etc.)

**Day 5: Wire Event Handlers**
- [ ] Register all event handlers
- [ ] Test cross-context communication
- [ ] Remove all direct cross-module imports

**Day 6-7: Outbox Pattern**
- [ ] Update EventMixin to use EventBus
- [ ] Create background worker to poll outbox
- [ ] Publish events to Redis/Pub/Sub

---

### **WEEK 3: AI Integration Pipeline**

#### AI Orchestrator as Domain Service

```python
# bounded_contexts/commodity_trading/domain/services/ai_recommendation_service.py
class AIRecommendationService:
    """Domain service using AI (provider-agnostic)"""
    
    def __init__(self, orchestrator: BaseAIOrchestrator):
        self.orchestrator = orchestrator
    
    async def suggest_commodity_alternatives(
        self, 
        commodity: str, 
        quality_specs: dict
    ) -> List[CommodityRecommendation]:
        """AI-powered commodity suggestions"""
        
        request = AIRequest(
            task_type=AITaskType.RECOMMENDATION,
            prompt=f"Suggest alternatives for {commodity}",
            context=quality_specs
        )
        
        result = await self.orchestrator.execute(request)
        return self._parse_recommendations(result)
```

#### Integration Points

**1. Requirement Creation (AI Suggestions)**
```python
# bounded_contexts/commodity_trading/application/commands/create_requirement.py
class CreateRequirementHandler:
    
    async def handle(self, command: CreateRequirement):
        # 1. Create requirement (domain logic)
        requirement = Requirement.create(...)
        
        # 2. AI suggestions (domain service)
        suggestions = await self.ai_service.suggest_commodity_alternatives(
            requirement.commodity,
            requirement.quality_specs
        )
        
        requirement.add_ai_suggestions(suggestions)
        
        # 3. Save & emit event
        await self.repo.save(requirement)
        await self.event_bus.publish(RequirementCreated(...))
```

**2. Availability Quality Grading (AI Vision)**
```python
# bounded_contexts/commodity_trading/application/commands/create_availability.py
class CreateAvailabilityHandler:
    
    async def handle(self, command: CreateAvailability):
        # 1. AI quality grading from images
        if command.sample_images:
            quality_grade = await self.ai_vision_service.grade_quality(
                command.sample_images,
                command.commodity_type
            )
        
        # 2. Create availability with AI grade
        availability = Availability.create(
            ai_quality_grade=quality_grade,
            ...
        )
```

**3. Matching Score (AI-Enhanced)**
```python
# bounded_contexts/commodity_trading/domain/services/matching_service.py
class MatchingService:
    
    async def calculate_match_score(
        self,
        requirement: Requirement,
        availability: Availability
    ) -> MatchScore:
        # 1. Rule-based scoring (existing logic)
        rule_score = self._rule_based_score(requirement, availability)
        
        # 2. AI-enhanced scoring
        ai_score = await self.ai_scoring_service.score_match(
            requirement, 
            availability
        )
        
        # 3. Weighted combination
        return MatchScore(
            rule_based=rule_score,
            ai_enhanced=ai_score,
            final=0.6 * rule_score + 0.4 * ai_score
        )
```

#### Tasks

**Day 1-2: AI Domain Services**
- [ ] AIRecommendationService
- [ ] AIQualityGradingService  
- [ ] AIScoringService

**Day 3-4: Integration into Use Cases**
- [ ] CreateRequirementHandler → AI suggestions
- [ ] CreateAvailabilityHandler → AI quality grading
- [ ] MatchingService → AI-enhanced scoring

**Day 5: Event-Driven AI**
- [ ] Subscribe to events → Trigger AI analysis
- [ ] Example: RequirementCreated → AI finds similar past requirements

---

### **WEEK 4: Microservices Preparation**

#### API Gateway Pattern

```python
# backend/api_gateway/
├── routes/
│   ├── identity_routes.py      # Proxy to identity context
│   ├── partners_routes.py      # Proxy to partner context
│   └── trading_routes.py       # Proxy to trading context
├── middleware/
│   ├── auth.py                 # Centralized auth
│   ├── rate_limit.py           # Rate limiting
│   └── logging.py              # Request logging
└── main.py                     # Gateway entry point
```

#### Internal API Contracts

```python
# Each bounded context exposes internal API
# bounded_contexts/identity/api/internal.py
class IdentityInternalAPI:
    """API for internal context-to-context calls"""
    
    async def get_user(self, user_id: UUID) -> UserDTO:
        """Other contexts can call this"""

# bounded_contexts/partner_management/api/internal.py  
class PartnerInternalAPI:
    async def get_partner(self, partner_id: UUID) -> PartnerDTO:
        """Other contexts can call this"""
```

#### Database Per Context (Schemas)

```sql
-- PostgreSQL schemas (not separate databases yet)
CREATE SCHEMA identity;
CREATE SCHEMA partner_management;
CREATE SCHEMA commodity_trading;

-- Each context owns its schema
-- Future: Can split into separate databases
```

#### Docker Compose (Multi-Container Local)

```yaml
# docker-compose.yml
services:
  # Event Bus
  redis:
    image: redis:7-alpine
    
  # API Gateway
  api-gateway:
    build: ./backend/api_gateway
    ports: ["8000:8000"]
    
  # Bounded Contexts (still in one process, but separated)
  identity-service:
    build: ./backend/bounded_contexts/identity
    environment:
      EVENT_BUS: redis://redis:6379
      
  partner-service:
    build: ./backend/bounded_contexts/partner_management
    
  trading-service:
    build: ./backend/bounded_contexts/commodity_trading
```

#### Tasks

**Day 1-2: API Gateway**
- [ ] Create API Gateway with routing
- [ ] Centralized authentication
- [ ] Request/response logging

**Day 3: Internal APIs**
- [ ] Define internal API contracts
- [ ] Implement for each context

**Day 4: Database Schemas**
- [ ] Create PostgreSQL schemas per context
- [ ] Migrate tables to schemas

**Day 5: Docker Compose**
- [ ] Multi-container setup (local)
- [ ] Test inter-service communication

**Day 6-7: Cloud Deployment Prep**
- [ ] Create Kubernetes manifests
- [ ] Cloud Build configuration
- [ ] Terraform for GCP resources

---

## 📊 BEFORE & AFTER

### Before (Monolith)
```
- 18 modules in one codebase
- Direct imports everywhere
- Shared database, no boundaries
- AI as separate endpoints
- Deploy as one service
```

### After (Domain-Driven Microservices-Ready)
```
✅ 5 bounded contexts (clear domains)
✅ Event-driven communication only
✅ Database schema per context
✅ AI integrated into workflows
✅ Can extract microservices anytime
```

---

## 🎯 SUCCESS CRITERIA

### Week 1
- [ ] All bounded contexts created
- [ ] 2 contexts fully migrated (identity, partners)
- [ ] No cross-context imports

### Week 2
- [ ] Event bus working (Redis local, Pub/Sub ready)
- [ ] All domain events defined
- [ ] Cross-context communication via events

### Week 3
- [ ] AI integrated into 3 workflows
- [ ] Event-driven AI analytics
- [ ] All AI calls through orchestrator

### Week 4
- [ ] API Gateway functional
- [ ] Internal APIs defined
- [ ] Docker Compose multi-container working
- [ ] Ready to deploy to GCP

---

## 🚀 DEPLOYMENT STRATEGY

### Phase 1: Local Development (Week 1-4)
- Bounded contexts in one repo
- Redis event bus
- Single database (PostgreSQL schemas)

### Phase 2: Cloud Deployment (Week 5-6)
- Deploy to Google Cloud Run (still monolith)
- Switch to Pub/Sub event bus
- Cloud SQL (still single database)

### Phase 3: True Microservices (Month 3-4)
- Extract one service at a time
- Separate databases per service
- Kubernetes deployment

---

## 💰 COST PROJECTION

### Local Development (Week 1-4)
- $0 (Redis, PostgreSQL local)

### Cloud Monolith (Month 2-3)
- ~₹8,000-12,000/month
- Cloud Run, Cloud SQL, Pub/Sub

### Microservices (Month 4+)
- ~₹25,000-40,000/month
- Multiple Cloud Run services, Kubernetes

---

## 🎓 LEARNING RESOURCES

- [ ] Domain-Driven Design (Eric Evans)
- [ ] Building Microservices (Sam Newman)
- [ ] Event-Driven Architecture (Martin Fowler)
- [ ] Google Cloud Architecture Framework

---

## ✅ READY TO START?

Next step: Create bounded context structure and start migration.

**Command to execute:**
```bash
# Start Week 1, Day 1
```
