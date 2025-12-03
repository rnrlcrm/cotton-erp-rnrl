"""
AI Infrastructure Configuration

Settings for AI models, services, and caching.
"""

from __future__ import annotations

import os
from typing import Optional
from pydantic_settings import BaseSettings


class AISettings(BaseSettings):
    """
    AI infrastructure settings.
    
    Environment variables:
    - AI_EMBEDDING_MODEL: Sentence Transformer model name
    - AI_EMBEDDING_CACHE_DIR: Model cache directory
    - AI_EMBEDDING_DEVICE: Device for model ('cpu', 'cuda', 'mps')
    - AI_TRANSLATION_CACHE_SIZE: Number of translations to cache
    - OPENAI_API_KEY: OpenAI API key (for GPT-4, optional)
    """
    
    # Embedding settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_cache_dir: str = os.path.expanduser("~/.cache/huggingface")
    embedding_device: Optional[str] = None  # Auto-detect
    embedding_dim: int = 384
    
    # Translation settings
    translation_cache_size: int = 10000
    default_language: str = "en"
    
    # OpenAI settings (optional, for GPT-4)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_max_tokens: int = 4000
    openai_temperature: float = 0.7
    
    # Vector search settings
    vector_search_threshold: float = 0.75  # Minimum similarity score
    vector_search_top_k: int = 20  # Number of results
    
    class Config:
        env_prefix = "AI_"
        case_sensitive = False


# Singleton settings
_ai_settings: Optional[AISettings] = None


def get_ai_settings() -> AISettings:
    """Get AI settings singleton."""
    global _ai_settings
    if _ai_settings is None:
        _ai_settings = AISettings()
    return _ai_settings
