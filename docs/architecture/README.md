# Architecture Documentation

## Overview

Cotton ERP is built using **Enterprise Hybrid Architecture** combining Domain-Driven Design (DDD), Clean Architecture, and Event-Driven Architecture principles.

## Architecture Layers

### 1. Presentation Layer
- **Frontend**: React + Vite (Web)
- **Mobile**: React Native (iOS/Android)
- **API Gateway**: FastAPI REST endpoints

### 2. Application Layer
- **API Routes**: `/api/v1/routers`
- **Use Cases**: Business logic orchestration
- **DTOs**: Request/Response schemas using Pydantic

### 3. Domain Layer
- **Entities**: Pure business objects
- **Value Objects**: Immutable domain concepts
- **Aggregates**: Consistency boundaries
- **Domain Services**: Complex business logic

### 4. Infrastructure Layer
- **Repositories**: Data access implementation
- **Adapters**: External service integration
- **Gateways**: Third-party API clients
- **Workers**: Background job processing

## Technology Stack

### Backend
- **Framework**: FastAPI 0.109+
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **Migration**: Alembic
- **Task Queue**: Celery + RabbitMQ
- **Caching**: Redis

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite 5
- **State Management**: Redux Toolkit / Zustand
- **Data Fetching**: TanStack Query
- **UI Components**: Headless UI + Tailwind CSS
- **Form Handling**: React Hook Form + Zod

### Mobile
- **Framework**: React Native 0.73
- **Navigation**: React Navigation 6
- **State Management**: Redux Toolkit
- **UI Library**: React Native Paper

### Database
- **Primary**: PostgreSQL 15
- **Caching**: Redis 7
- **Search**: PostgreSQL Full-Text Search

### DevOps
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions
- **IaC**: Terraform
- **Monitoring**: Prometheus + Grafana

## Design Patterns

### Backend Patterns
1. **Repository Pattern**: Data access abstraction
2. **Service Layer Pattern**: Business logic encapsulation
3. **Factory Pattern**: Object creation
4. **Strategy Pattern**: Algorithm selection
5. **Observer Pattern**: Event handling
6. **Dependency Injection**: Loose coupling

### Frontend Patterns
1. **Container/Presenter**: Component organization
2. **Custom Hooks**: Logic reusability
3. **Compound Components**: Complex UI composition
4. **Render Props**: Cross-cutting concerns
5. **Context + Hooks**: State management

## Module Architecture

Each business module follows this structure:

```
module_name/
├── models/          # SQLAlchemy models
├── services/        # Business logic
├── repositories/    # Data access
├── schemas/         # Pydantic schemas
└── routes/          # FastAPI routes
```

### Module Flow

```
Request → Route → Service → Repository → Database
                ↓
         Domain Logic
                ↓
         Response Schema
```

## Event-Driven Architecture

### Event Flow
```
Action → Event Dispatcher → Event Handlers → Side Effects
                          ↓
                    Event Subscribers
```

### Event Types
- **Domain Events**: Business-critical events
- **Integration Events**: Cross-module communication
- **System Events**: Infrastructure events

## AI Architecture

### AI Layer Components
1. **Models**: ML/DL models (price prediction, fraud detection)
2. **Orchestrators**: AI workflow coordination
3. **Assistants**: Role-based AI agents
4. **Embeddings**: Document/data vectorization
5. **Analytics**: AI-powered insights

### AI Workflow
```
User Input → Orchestrator → Prompt Engineering → LLM → Response Processing → User Output
              ↓                                           ↓
        Context Building                          Result Validation
```

## Security Architecture

### Authentication Flow
```
Login → JWT Generation → Access Token + Refresh Token
         ↓
    Token Storage (HttpOnly Cookie)
         ↓
    Subsequent Requests (Bearer Token)
         ↓
    Token Validation → RBAC Check → Resource Access
```

### RBAC Model
- **Roles**: Admin, Buyer, Seller, Broker, Controller, Quality, Accountant
- **Permissions**: Module-based + action-based
- **Resources**: API endpoints, UI components

## Data Flow

### Trade Flow Example
```
1. Trade Creation (Buyer)
   ↓
2. Trade Validation (Business Rules)
   ↓
3. Contract Generation (Contract Engine)
   ↓
4. Quality Check Request (Quality Module)
   ↓
5. Logistics Request (Logistics Module)
   ↓
6. Inward Entry (Controller Module)
   ↓
7. Quality Test (Quality Module)
   ↓
8. Payment Processing (Payment Engine)
   ↓
9. Settlement (Accounting Module)
```

## Integration Points

### External Integrations
1. **GST API**: Tax compliance
2. **CCI API**: Commodity prices
3. **Bank APIs**: Payment verification
4. **Payment Gateways**: Razorpay, Stripe
5. **Email/SMS**: Notifications
6. **Cloud Storage**: Document management

## Scalability Strategy

### Horizontal Scaling
- Stateless API servers
- Load balancer (Nginx/HAProxy)
- Database read replicas
- Redis cluster for caching

### Vertical Scaling
- Database optimization
- Query optimization
- Caching strategies
- CDN for static assets

## Monitoring & Observability

### Metrics
- Request rate
- Error rate
- Response time
- Database query performance
- Worker queue size

### Logging
- Structured logging (JSON)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Centralized logging (ELK Stack)

### Tracing
- Distributed tracing
- Request ID propagation
- Performance profiling

## Deployment Architecture

### Development
- Docker Compose
- Hot reload enabled
- Local databases

### Staging
- Kubernetes cluster
- Mirrored production setup
- Test data

### Production
- Kubernetes cluster (multi-zone)
- Auto-scaling enabled
- High availability
- Disaster recovery

## Best Practices

1. **Code Organization**: Follow module structure consistently
2. **Error Handling**: Use custom exceptions and proper HTTP status codes
3. **Validation**: Validate at boundaries (API, database)
4. **Testing**: Unit, integration, and e2e tests
5. **Documentation**: Keep docs up-to-date
6. **Security**: Follow OWASP guidelines
7. **Performance**: Monitor and optimize continuously

## Future Enhancements

1. GraphQL API support
2. Real-time features with WebSockets
3. Microservices migration (if needed)
4. Advanced ML models
5. Mobile app enhancements
6. Multi-tenancy support

---

For detailed module documentation, refer to `/docs/modules/[module-name]/README.md`
