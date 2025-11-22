"""
Domain Repositories Package

All module repositories extend BaseRepository for automatic data isolation.
"""

from backend.domain.repositories.base import BaseRepository, ModelType

__all__ = [
    'BaseRepository',
    'ModelType',
]
