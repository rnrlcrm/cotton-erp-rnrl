"""
Business Partners Module

External companies (buyers, sellers, brokers, transporters) that interact with the system.
This is a minimal model providing the FK foundation for data isolation.

NOTE: This module now re-exports from modules.partners to avoid duplication.
"""

from backend.modules.partners.models import BusinessPartner

__all__ = ['BusinessPartner']
