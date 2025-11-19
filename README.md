# Cotton ERP - Enterprise Commodity Trading + ERP + AI Automation System

## 🎯 Overview

A comprehensive, production-grade enterprise system for commodity trading, ERP operations, and AI-powered automation. Built with modern technology stack and clean architecture principles.

## 🏗️ Architecture

### Technology Stack

- **Backend**: FastAPI + Python
- **Frontend**: React + Vite
- **Mobile**: React Native
- **Database**: PostgreSQL
- **Caching**: Redis
- **Messaging**: RabbitMQ / Kafka
- **Workers**: Celery / RQ
- **Storage**: GCS / AWS S3
- **Auth**: JWT + RBAC
- **Validation**: Pydantic

## 📁 Folder Structure

### Backend (Enterprise Hybrid Architecture)

```
backend/
├── app/                        # Core application runtime
│   ├── main.py                # FastAPI application entry point
│   ├── config.py              # Application configuration
│   ├── middleware.py          # Custom middleware
│   ├── startup.py             # Startup events
│   └── shutdown.py            # Shutdown events
│
├── core/                      # Core utilities and cross-cutting concerns
│   ├── security/              # Security utilities
│   │   ├── auth.py           # Authentication logic
│   │   ├── password.py       # Password hashing
│   │   └── encryption.py     # Encryption utilities
│   ├── rbac/                 # Role-Based Access Control
│   │   ├── permissions.py    # Permission definitions
│   │   ├── roles.py          # Role definitions
│   │   └── decorators.py     # RBAC decorators
│   ├── jwt/                  # JWT handling
│   │   ├── token.py          # Token generation/validation
│   │   └── refresh.py        # Token refresh logic
│   ├── settings/             # Settings management
│   │   ├── base.py           # Base settings
│   │   ├── development.py   # Development settings
│   │   └── production.py    # Production settings
│   ├── validators/           # Custom validators
│   │   ├── custom.py         # Custom validation logic
│   │   └── business.py       # Business rule validators
│   └── enums/                # Enumerations
│       ├── status.py         # Status enums
│       ├── roles.py          # Role enums
│       └── modules.py        # Module enums
│
├── api/v1/                    # API v1 routes
│   ├── routers/              # API route handlers
│   │   ├── trade_desk.py     # Trade desk endpoints
│   │   ├── sub_broker.py     # Sub-broker endpoints
│   │   ├── logistics.py      # Logistics endpoints
│   │   ├── controller.py     # Controller endpoints
│   │   ├── quality.py        # Quality endpoints
│   │   ├── accounting.py     # Accounting endpoints
│   │   ├── payment_engine.py # Payment endpoints
│   │   ├── contract_engine.py# Contract endpoints
│   │   ├── cci.py            # CCI endpoints
│   │   ├── risk_engine.py    # Risk engine endpoints
│   │   ├── dispute.py        # Dispute endpoints
│   │   ├── reports.py        # Reports endpoints
│   │   ├── settings.py       # Settings endpoints
│   │   ├── user_onboarding.py# User onboarding endpoints
│   │   ├── ocr.py            # OCR endpoints
│   │   ├── market_trends.py  # Market trends endpoints
│   │   ├── notifications.py  # Notifications endpoints
│   │   └── compliance.py     # Compliance endpoints
│   ├── dependencies/         # Dependency injection
│   │   ├── auth.py           # Auth dependencies
│   │   └── database.py       # Database dependencies
│   └── schemas/              # Common API schemas
│       └── common.py         # Common response schemas
│
├── modules/                   # Business modules (DDD style)
│   ├── trade_desk/           # Buyer-Seller Trading Desk
│   ├── sub_broker/           # Sub-Broker/Agent Module
│   ├── logistics/            # Logistics Module
│   ├── controller/           # Controller Module (inward/outward)
│   ├── quality/              # Quality Module (lab testing)
│   ├── accounting/           # Accounting Module (COA, Ledger, JV)
│   ├── payment_engine/       # Payment Engine (auto-reco, gateway)
│   ├── contract_engine/      # Contract Engine
│   ├── cci/                  # CCI Module
│   ├── risk_engine/          # Risk Engine
│   ├── dispute/              # Dispute Module
│   ├── reports/              # Reports (MIS, dashboards)
│   ├── settings/             # Settings Module
│   ├── user_onboarding/      # User onboarding & auth
│   ├── ocr/                  # OCR Engine
│   ├── market_trends/        # Market Trends Module
│   ├── notifications/        # Notifications Module
│   └── compliance/           # Compliance Module
│   └── [Each module contains:]
│       ├── models/           # Database models
│       ├── services/         # Business logic
│       ├── repositories/     # Data access layer
│       ├── schemas/          # Pydantic schemas
│       └── routes/           # Module-specific routes
│
├── domain/                    # Pure domain entities (DDD)
│   ├── entities/             # Domain entities
│   │   ├── trade.py          # Trade entity
│   │   ├── contract.py       # Contract entity
│   │   ├── logistics.py      # Logistics entity
│   │   ├── quality.py        # Quality entity
│   │   └── payment.py        # Payment entity
│   ├── value_objects/        # Value objects
│   │   ├── money.py          # Money value object
│   │   ├── address.py        # Address value object
│   │   └── contact.py        # Contact value object
│   ├── aggregates/           # Aggregate roots
│   │   └── trade_aggregate.py# Trade aggregate
│   └── repositories/         # Repository interfaces
│       └── base.py           # Base repository
│
├── events/                    # Event-driven architecture
│   ├── dispatchers/          # Event dispatchers
│   │   └── event_dispatcher.py
│   ├── handlers/             # Event handlers
│   │   ├── trade_handler.py
│   │   ├── payment_handler.py
│   │   └── notification_handler.py
│   └── subscribers/          # Event subscribers
│       ├── audit_subscriber.py
│       └── notification_subscriber.py
│
├── adapters/                  # External service adapters
│   ├── email/                # Email adapters
│   │   ├── smtp.py           # SMTP adapter
│   │   └── templates.py      # Email templates
│   ├── sms/                  # SMS adapters
│   │   └── twilio.py         # Twilio adapter
│   ├── ocr/                  # OCR adapters
│   │   ├── invoice.py        # Invoice OCR
│   │   ├── bilty.py          # Bilty OCR
│   │   └── quality_report.py # Quality report OCR
│   ├── payment/              # Payment gateway adapters
│   │   ├── razorpay.py       # Razorpay adapter
│   │   └── stripe.py         # Stripe adapter
│   ├── bank/                 # Banking adapters
│   │   ├── utr_verification.py
│   │   └── statement_parser.py
│   └── storage/              # Storage adapters
│       ├── s3.py             # AWS S3 adapter
│       └── gcs.py            # Google Cloud Storage adapter
│
├── gateways/                  # External API gateways
│   ├── gst/                  # GST API gateway
│   ├── bank/                 # Bank API gateway
│   ├── cci/                  # CCI API gateway
│   └── market_data/          # Market data API gateway
│
├── workers/                   # Background workers
│   ├── notification/         # Notification workers
│   │   ├── email_worker.py
│   │   └── sms_worker.py
│   ├── reconciliation/       # Reconciliation workers
│   │   ├── payment_worker.py
│   │   └── bank_worker.py
│   ├── ai_worker/            # AI workers
│   │   ├── prediction_worker.py
│   │   └── analysis_worker.py
│   └── scheduler/            # Scheduled tasks
│       └── tasks.py
│
├── db/                        # Database management
│   ├── migrations/           # Database migrations
│   ├── seeds/                # Database seeds
│   ├── schema/               # Schema definitions
│   └── session/              # Database session management
│
├── ai/                        # AI Layer
│   ├── models/               # AI Models
│   │   ├── price_prediction/ # Price prediction models
│   │   ├── fraud_detection/  # Fraud detection models
│   │   ├── quality_scoring/  # Quality scoring models
│   │   └── demand_forecasting/# Demand forecasting models
│   ├── orchestrators/        # AI Orchestrators
│   │   ├── trade/            # Trade orchestrator
│   │   ├── logistics/        # Logistics orchestrator
│   │   ├── quality/          # Quality orchestrator
│   │   ├── payment/          # Payment orchestrator
│   │   ├── contract/         # Contract orchestrator
│   │   └── dispute/          # Dispute orchestrator
│   ├── prompts/              # AI Prompts
│   │   ├── buyer/            # Buyer prompts
│   │   ├── seller/           # Seller prompts
│   │   ├── controller/       # Controller prompts
│   │   ├── broker/           # Broker prompts
│   │   ├── logistics/        # Logistics prompts
│   │   ├── quality/          # Quality prompts
│   │   ├── accounting/       # Accounting prompts
│   │   ├── dispute/          # Dispute prompts
│   │   ├── payment/          # Payment prompts
│   │   └── cci/              # CCI prompts
│   ├── workflows/            # AI Workflows (YAML)
│   │   ├── trade_workflow.yaml
│   │   ├── payment_workflow.yaml
│   │   ├── quality_workflow.yaml
│   │   ├── logistics_workflow.yaml
│   │   ├── contract_workflow.yaml
│   │   └── dispute_workflow.yaml
│   ├── assistants/           # AI Assistants
│   │   ├── buyer_assistant/  # Buyer assistant
│   │   ├── seller_assistant/ # Seller assistant
│   │   ├── controller_assistant/
│   │   ├── broker_assistant/
│   │   ├── logistics_assistant/
│   │   ├── quality_assistant/
│   │   ├── accounting_assistant/
│   │   ├── dispute_assistant/
│   │   ├── payment_assistant/
│   │   └── cci_assistant/
│   ├── embeddings/           # AI Embeddings
│   │   ├── document/         # Document embeddings
│   │   ├── contract/         # Contract embeddings
│   │   └── quality_report/   # Quality report embeddings
│   ├── analytics/            # AI Analytics
│   │   ├── market/           # Market analytics
│   │   ├── trading/          # Trading analytics
│   │   └── operational/      # Operational analytics
│   └── evaluators/           # AI Evaluators
│       ├── model/            # Model evaluators
│       ├── performance/      # Performance evaluators
│       └── quality/          # Quality evaluators
│
└── tests/                     # Test suite
    ├── unit/                 # Unit tests
    ├── integration/          # Integration tests
    ├── e2e/                  # End-to-end tests
    └── fixtures/             # Test fixtures
```

### Frontend (React + Vite)

```
frontend/
├── src/
│   ├── components/           # Reusable components
│   │   ├── common/           # Common components
│   │   ├── trade_desk/       # Trade desk components
│   │   ├── logistics/        # Logistics components
│   │   ├── quality/          # Quality components
│   │   ├── accounting/       # Accounting components
│   │   ├── reports/          # Reports components
│   │   ├── settings/         # Settings components
│   │   └── dashboard/        # Dashboard components
│   ├── pages/                # Page components
│   │   ├── trade_desk/       # Trade desk pages
│   │   ├── sub_broker/       # Sub-broker pages
│   │   ├── logistics/        # Logistics pages
│   │   ├── controller/       # Controller pages
│   │   ├── quality/          # Quality pages
│   │   ├── accounting/       # Accounting pages
│   │   ├── payment_engine/   # Payment engine pages
│   │   ├── contract_engine/  # Contract engine pages
│   │   ├── cci/              # CCI pages
│   │   ├── risk_engine/      # Risk engine pages
│   │   ├── dispute/          # Dispute pages
│   │   ├── reports/          # Reports pages
│   │   ├── settings/         # Settings pages
│   │   ├── user_onboarding/  # User onboarding pages
│   │   ├── market_trends/    # Market trends pages
│   │   └── dashboard/        # Dashboard pages
│   ├── hooks/                # Custom React hooks
│   ├── services/             # API services
│   │   ├── api/              # API client
│   │   ├── auth/             # Auth service
│   │   ├── trade/            # Trade service
│   │   ├── logistics/        # Logistics service
│   │   ├── quality/          # Quality service
│   │   ├── accounting/       # Accounting service
│   │   ├── payment/          # Payment service
│   │   ├── contract/         # Contract service
│   │   └── reports/          # Reports service
│   ├── utils/                # Utility functions
│   ├── store/                # State management (Redux/Zustand)
│   │   ├── slices/           # State slices
│   │   └── middleware/       # Middleware
│   ├── routes/               # Route configuration
│   ├── layouts/              # Layout components
│   ├── assets/               # Static assets
│   ├── styles/               # Global styles
│   └── types/                # TypeScript types
└── public/                   # Public assets
```

### Mobile (React Native)

```
mobile/
├── src/
│   ├── components/           # Reusable components
│   │   ├── common/           # Common components
│   │   ├── trade/            # Trade components
│   │   ├── logistics/        # Logistics components
│   │   └── quality/          # Quality components
│   ├── screens/              # Screen components
│   │   ├── trade_desk/       # Trade desk screens
│   │   ├── logistics/        # Logistics screens
│   │   ├── quality/          # Quality screens
│   │   ├── reports/          # Reports screens
│   │   ├── settings/         # Settings screens
│   │   ├── dashboard/        # Dashboard screens
│   │   └── auth/             # Auth screens
│   ├── navigation/           # Navigation configuration
│   ├── services/             # API services
│   ├── utils/                # Utility functions
│   ├── store/                # State management
│   ├── assets/               # Static assets
│   └── types/                # TypeScript types
├── android/                  # Android native code
└── ios/                      # iOS native code
```

### Infrastructure

```
infra/
├── docker/                   # Docker configurations
│   ├── backend/              # Backend Dockerfiles
│   ├── frontend/             # Frontend Dockerfiles
│   ├── mobile/               # Mobile Dockerfiles
│   ├── nginx/                # Nginx configuration
│   ├── postgres/             # PostgreSQL configuration
│   ├── redis/                # Redis configuration
│   └── rabbitmq/             # RabbitMQ configuration
├── kubernetes/               # Kubernetes manifests
│   ├── deployments/          # Deployment configs
│   ├── services/             # Service configs
│   ├── configmaps/           # ConfigMaps
│   ├── secrets/              # Secrets
│   └── ingress/              # Ingress configs
├── terraform/                # Infrastructure as Code
│   ├── aws/                  # AWS resources
│   ├── gcp/                  # GCP resources
│   └── azure/                # Azure resources
├── ansible/                  # Ansible playbooks
└── scripts/                  # Utility scripts
    ├── deploy/               # Deployment scripts
    ├── backup/               # Backup scripts
    └── monitoring/           # Monitoring scripts
```

### Documentation

```
docs/
├── modules/                  # Module-specific documentation
│   ├── accounting/           # Accounting module docs
│   ├── trade_desk/           # Trade desk module docs
│   ├── logistics/            # Logistics module docs
│   ├── quality/              # Quality module docs
│   ├── settings/             # Settings module docs
│   ├── reports/              # Reports module docs
│   ├── market_trends/        # Market trends module docs
│   ├── payment_engine/       # Payment engine module docs
│   ├── cci_module/           # CCI module docs
│   ├── sub_broker/           # Sub-broker module docs
│   ├── user_onboarding/      # User onboarding module docs
│   ├── compliance/           # Compliance module docs
│   ├── notifications/        # Notifications module docs
│   ├── ocr/                  # OCR module docs
│   ├── security_rbac/        # Security & RBAC docs
│   ├── ai_orchestration/     # AI orchestration docs
│   ├── contract_engine/      # Contract engine docs
│   └── dispute/              # Dispute module docs
├── architecture/             # Architecture documentation
├── api/                      # API documentation
├── deployment/               # Deployment documentation
├── development/              # Development documentation
└── user_guides/              # User guides
```

## 📦 System Modules

### 1. Trade Desk Module
Buyer-Seller trading operations, order management, trade lifecycle

### 2. Sub-Broker Module
Sub-broker/agent management, commission tracking, performance metrics

### 3. Logistics Module
Lorry request, assignment, tracking, route optimization

### 4. Controller Module
Inward/outward stock management, warehouse operations

### 5. Quality Module
Lab testing, quality scoring, quality reports, sample management

### 6. Accounting Module
Chart of Accounts, General Ledger, Journal Vouchers, Payments, Receipts, Settlement

### 7. Payment Engine
Auto-reconciliation, payment gateway integration, UTR verification

### 8. Contract Engine
Contract creation, negotiation, digital signing, template management

### 9. CCI Module
CCI integration, price updates, compliance

### 10. Risk Engine
Risk scoring, fraud detection, risk mitigation

### 11. Dispute Module
Dispute management, resolution workflow, escalation

### 12. Reports Module
MIS reports, dashboards, analytics, data visualization

### 13. Settings Module
Commodities, organization, locations, FY years, roles, configurations

### 14. User Onboarding Module
User registration, authentication, RBAC, JWT, profile management

### 15. OCR Engine
Invoice OCR, Bilty OCR, Quality report OCR, document processing

### 16. Market Trends Module
Price prediction, trend analysis, demand forecasting, market intelligence

### 17. Notifications Module
Email, SMS, push notifications, alerts

### 18. Compliance Module
Regulatory compliance, audit trails, compliance checks

## 🤖 AI Layer

### AI Orchestrators
- Trade orchestrator
- Logistics orchestrator
- Quality orchestrator
- Payment orchestrator
- Contract orchestrator
- Dispute orchestrator

### AI Assistants
- Buyer assistant
- Seller assistant
- Controller assistant
- Sub-broker assistant
- Logistics assistant
- Quality assistant
- Accounting assistant
- Dispute assistant
- Payment assistant
- CCI assistant

### AI Models
- Price prediction
- Fraud detection
- Quality scoring
- Demand forecasting

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose

### Installation

1. Clone the repository
```bash
git clone https://github.com/rnrlcrm/cotton-erp-rnrl.git
cd cotton-erp-rnrl
```

2. Setup backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Setup frontend
```bash
cd frontend
npm install
```

4. Setup mobile
```bash
cd mobile
npm install
```

5. Configure environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. Run with Docker Compose
```bash
docker-compose up -d
```

## 📝 Development

### Backend Development
```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Mobile Development
```bash
cd mobile
npm start
```

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Mobile tests
cd mobile
npm test
```

## 📚 Documentation

Complete documentation is available in the `/docs` directory:
- [Architecture Overview](docs/architecture/README.md)
- [API Documentation](docs/api/README.md)
- [Deployment Guide](docs/deployment/README.md)
- [Development Guide](docs/development/README.md)
- [User Guides](docs/user_guides/README.md)

## 🔐 Security

- JWT-based authentication
- Role-Based Access Control (RBAC)
- Data encryption at rest and in transit
- Regular security audits
- OWASP compliance

## 🤝 Contributing

Please read [CONTRIBUTING.md](docs/development/contributing.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is proprietary and confidential.

## 👥 Team

- Backend Team
- Frontend Team
- Mobile Team
- AI/ML Team
- DevOps Team
- QA Team

## 📞 Support

For support, email support@cottonerp.com or join our Slack channel.

---

**Built with ❤️ for the Commodity Trading Industry**
