"""
AI Jobs Package

Background jobs for AI operations.
"""

from backend.ai.jobs.vector_sync import EmbeddingSyncJob

__all__ = [
    "EmbeddingSyncJob",
]
