"""
Availability Engine REST API Routes

Re-exports the router from availability_routes.py
"""

from backend.modules.trade_desk.routes.availability_routes import router

__all__ = ["router"]
