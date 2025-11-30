"""
Abstract AI Orchestrator Interface

This interface abstracts AI provider implementations for 15-year flexibility.
NO business logic - pure abstraction layer.

Benefits:
- Swap AI providers (OpenAI → Anthropic → Google → future) without changing business code
- Test with mock implementations
- Track all AI decisions in one place
- Unified observability for all AI calls
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class AIProvider(str, Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    CUSTOM = "custom"


class AITaskType(str, Enum):
    """Types of AI tasks for routing and monitoring."""
    TEXT_GENERATION = "text_generation"
    CLASSIFICATION = "classification"
    SCORING = "scoring"
    RECOMMENDATION = "recommendation"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"
    CHAT = "chat"


@dataclass
class AIRequest:
    """Standardized AI request."""
    task_type: AITaskType
    prompt: str
    context: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AIResponse:
    """Standardized AI response with explainability."""
    result: Any
    provider: AIProvider
    model: str
    task_type: AITaskType
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    request_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BaseAIOrchestrator(ABC):
    """
    Abstract base class for all AI orchestrators.
    
    This ensures consistent interface across all AI providers for 15 years.
    Business logic NEVER directly imports OpenAI, Anthropic, etc.
    """
    
    def __init__(self, provider: AIProvider, **config):
        """
        Initialize orchestrator.
        
        Args:
            provider: Which AI provider this orchestrator uses
            **config: Provider-specific configuration
        """
        self.provider = provider
        self.config = config
    
    @abstractmethod
    async def execute(self, request: AIRequest) -> AIResponse:
        """
        Execute AI request and return response.
        
        This is the ONLY method business logic should call.
        All AI interactions go through this single interface.
        
        Args:
            request: Standardized AI request
            
        Returns:
            Standardized AI response with explainability
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if AI provider is healthy.
        
        Returns:
            True if provider is available and working
        """
        pass
    
    async def execute_with_fallback(
        self,
        request: AIRequest,
        fallback_orchestrator: Optional['BaseAIOrchestrator'] = None
    ) -> AIResponse:
        """
        Execute with optional fallback to another provider.
        
        This enables provider redundancy for 15-year resilience.
        """
        try:
            return await self.execute(request)
        except Exception as e:
            if fallback_orchestrator:
                # Log primary failure
                import logging
                logging.warning(
                    f"AI provider {self.provider} failed, using fallback: {e}"
                )
                return await fallback_orchestrator.execute(request)
            raise
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider metadata for observability."""
        return {
            "provider": self.provider.value,
            "config": {k: v for k, v in self.config.items() if k not in ['api_key', 'secret']}
        }


class AIOrchestrationError(Exception):
    """Base exception for AI orchestration errors."""
    pass


class AIProviderUnavailableError(AIOrchestrationError):
    """AI provider is unavailable or unhealthy."""
    pass


class AIRequestValidationError(AIOrchestrationError):
    """AI request is invalid."""
    pass
