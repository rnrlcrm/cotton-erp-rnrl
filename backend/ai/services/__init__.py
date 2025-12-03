"""
AI Services Package

Shared AI services for the entire platform.
"""

from backend.ai.services.language_service import LanguageService
from backend.ai.services.embedding_service import EmbeddingService

__all__ = [
    "LanguageService",
    "EmbeddingService",
]
