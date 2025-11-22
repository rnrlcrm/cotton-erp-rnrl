"""
Business Partner Module

Handles all partner types with data isolation:
- Seller, Buyer, Trader (commodity trading)
- Broker, Sub-Broker (intermediaries)
- Transporter, Controller, Financer, Shipping Agent (service providers)
- Importer, Exporter (international trade)

Features:
- GST/Tax auto-fetch
- Auto-geocoding
- Risk assessment
- Yearly KYC renewal
- Multi-location support
- Automated notifications (KYC reminders, approvals)
- Export to Excel/CSV
- PDF KYC register
- Dashboard analytics
"""

from backend.modules.partners.router import router
from backend.modules.partners.event_handlers import register_partner_event_handlers
from backend.modules.partners.jobs import register_partner_jobs

__all__ = [
    "router",
    "register_partner_event_handlers",
    "register_partner_jobs",
]
