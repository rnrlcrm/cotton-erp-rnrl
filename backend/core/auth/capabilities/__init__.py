"""Capability-Based Authorization Module"""

from backend.core.auth.capabilities.decorators import RequireCapability, check_capability, require_capability
from backend.core.auth.capabilities.definitions import CAPABILITY_METADATA, Capabilities
from backend.core.auth.capabilities.models import Capability, RoleCapability, UserCapability
from backend.core.auth.capabilities.service import CapabilityService, get_capability_service

__all__ = [
    "Capabilities",
    "CAPABILITY_METADATA",
    "Capability",
    "UserCapability",
    "RoleCapability",
    "CapabilityService",
    "get_capability_service",
    "RequireCapability",
    "require_capability",
    "check_capability",
]
