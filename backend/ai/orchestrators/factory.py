"""
AI Orchestrator Factory

Provides singleton access to configured AI orchestrator.
Business logic uses this to get orchestrator instance.

NO business logic here - pure factory pattern.
"""

from typing import Optional
import os

from backend.ai.orchestrators.base import BaseAIOrchestrator, AIProvider
from backend.ai.orchestrators.langchain_adapter import LangChainOrchestratorAdapter


# Singleton instance
_orchestrator: Optional[BaseAIOrchestrator] = None


def get_orchestrator(
    provider: Optional[AIProvider] = None,
    **config
) -> BaseAIOrchestrator:
    """
    Get or create AI orchestrator instance.
    
    This is the ONLY way business logic should get an orchestrator.
    
    Args:
        provider: Which AI provider to use (defaults to env config)
        **config: Provider-specific configuration
        
    Returns:
        Configured AI orchestrator
        
    Example:
        ```python
        from backend.ai.orchestrators.factory import get_orchestrator
        from backend.ai.orchestrators.base import AIRequest, AITaskType
        
        orchestrator = get_orchestrator()
        response = await orchestrator.execute(
            AIRequest(
                task_type=AITaskType.SCORING,
                prompt="Score this match from 0-100: ...",
                temperature=0.0
            )
        )
        score = response.result["score"]
        ```
    """
    global _orchestrator
    
    if _orchestrator is None:
        # Determine provider from env or parameter
        provider_name = provider or os.getenv("AI_PROVIDER", "openai")
        
        if isinstance(provider_name, str):
            provider_name = provider_name.lower()
            if provider_name == "openai":
                provider = AIProvider.OPENAI
            elif provider_name == "anthropic":
                provider = AIProvider.ANTHROPIC
            elif provider_name == "google":
                provider = AIProvider.GOOGLE
            else:
                provider = AIProvider.OPENAI  # Default
        
        # Create orchestrator based on provider
        if provider == AIProvider.OPENAI:
            _orchestrator = LangChainOrchestratorAdapter(
                api_key=config.get("api_key") or os.getenv("OPENAI_API_KEY"),
                model_name=config.get("model_name", "gpt-4-turbo-preview"),
                temperature=config.get("temperature", 0.7),
            )
        elif provider == AIProvider.ANTHROPIC:
            # Future: Anthropic adapter
            raise NotImplementedError("Anthropic adapter coming soon")
        elif provider == AIProvider.GOOGLE:
            # Future: Google Gemini adapter
            raise NotImplementedError("Google Gemini adapter coming soon")
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    return _orchestrator


def reset_orchestrator():
    """Reset singleton (useful for testing)."""
    global _orchestrator
    _orchestrator = None
