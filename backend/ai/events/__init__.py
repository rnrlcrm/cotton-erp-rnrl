"""
AI Events Package

Event handlers for AI operations.
"""

from backend.ai.events.handlers import (
    register_ai_event_handlers,
    handle_requirement_created,
    handle_requirement_updated,
    handle_availability_created,
    handle_availability_updated,
)

__all__ = [
    "register_ai_event_handlers",
    "handle_requirement_created",
    "handle_requirement_updated",
    "handle_availability_created",
    "handle_availability_updated",
]
