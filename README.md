# Commodity ERP - Modular Monolith with Event-Driven Architecture

**Status:** Production Ready  
**Architecture:** Modular Monolith + Event Bus  
**Last Updated:** December 2, 2025

## 🏗️ Architecture

- **Pattern:** Modular Monolith with Event-Driven Communication
- **Modules:** 24 independent modules with clear boundaries
- **Event Bus:** Google Pub/Sub for async workflows
- **Database:** PostgreSQL with per-module schemas
- **Scaling:** Event-based, horizontal scaling ready

## 🚀 Quick Start

```bash
make setup    # Install dependencies
make dev      # Run development server
make test     # Run test suite
```

## 📦 Module Structure

```
backend/modules/
├── partners/          # Business partner management
├── trade_desk/        # Trading operations
├── risk/              # Risk assessment
├── payment_engine/    # Payment processing
├── notifications/     # Email/SMS/WhatsApp
└── ... 19 more modules
```

## 🔗 Event-Driven Communication

Modules communicate via events (not direct imports):
- ✅ Async workflows (notifications, analytics)
- ✅ Audit trail (all events logged)
- ✅ Scalability (add subscribers without code changes)

## 📖 Documentation

See `/docs` folder for detailed technical documentation.
