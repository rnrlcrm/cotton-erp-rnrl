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
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


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
    """
    Standardized AI request with memory and context.
    
    Enhanced with:
    - user_id: For guardrails and usage tracking
    - conversation_id: For conversation history
    - conversation_history: Previous messages for context
    - user_context: User preferences and patterns
    """
    task_type: AITaskType
    prompt: str
    context: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Memory and context (NEW)
    user_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    user_context: Optional[Dict[str, Any]] = None


@dataclass
class AIResponse:
    """
    Standardized AI response with explainability and cost tracking.
    
    Enhanced with:
    - cost: Actual cost in USD
    - guardrail_passed: Whether request passed guardrails
    - memory_loaded: Whether memory was loaded successfully
    """
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
    
    # Cost and guardrails (NEW)
    cost: float = 0.0
    guardrail_passed: bool = True
    memory_loaded: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BaseAIOrchestrator(ABC):
    """
    Abstract base class for all AI orchestrators.
    
    This ensures consistent interface across all AI providers for 15 years.
    Business logic NEVER directly imports OpenAI, Anthropic, etc.
    
    Enhanced with:
    - Guardrails integration (rate limiting, cost control)
    - Memory loading (conversation history, user context)
    - Automatic usage tracking
    """
    
    def __init__(
        self,
        provider: AIProvider,
        enable_guardrails: bool = True,
        enable_memory: bool = True,
        **config
    ):
        """Initialize orchestrator with provider and features."""
        self.provider = provider
        self.enable_guardrails = enable_guardrails
        self.enable_memory = enable_memory
        self.config = config
        self._guardrails = None
        self._memory_loader = None
    
    async def execute(self, request: AIRequest) -> AIResponse:
        """
        Execute AI request with guardrails and memory.
        
        This is the ONLY method business logic should call.
        All AI interactions go through this single interface.
        
        Flow:
        1. Check guardrails (rate limit, cost, content)
        2. Load memory (conversation history, user context)
        3. Execute AI request (provider-specific)
        4. Record usage (tokens, cost)
        5. Return response
        
        Args:
            request: Standardized AI request
            
        Returns:
            Standardized AI response with explainability
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Step 1: Check guardrails
        if self.enable_guardrails and request.user_id:
            guardrails = await self._get_guardrails()
            
            # Estimate tokens (rough: 4 chars per token)
            tokens_estimate = len(request.prompt) // 4
            
            violation = await guardrails.check_request(
                user_id=request.user_id,
                tokens_estimate=tokens_estimate,
                prompt=request.prompt
            )
            
            if violation:
                # Return error response
                logger.warning(f"Guardrail violation: {violation.type} - {violation.message}")
                return AIResponse(
                    result={"error": violation.message, "type": violation.type},
                    provider=self.provider,
                    model="blocked",
                    task_type=request.task_type,
                    guardrail_passed=False,
                )
        
        # Step 2: Load memory
        if self.enable_memory and request.user_id:
            try:
                memory_loader = await self._get_memory_loader()
                
                # Load if not already provided
                if not request.conversation_history:
                    memory = await memory_loader.load_context(
                        user_id=request.user_id,
                        conversation_id=request.conversation_id
                    )
                    
                    request.conversation_history = memory.get("conversation_history", [])
                    request.user_context = memory.get("preferences", {})
                
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")
        
        # Step 3: Execute provider-specific request
        response = await self._execute_impl(request)
        
        # Step 4: Record usage
        if self.enable_guardrails and request.user_id:
            guardrails = await self._get_guardrails()
            await guardrails.record_usage(
                user_id=request.user_id,
                tokens_used=response.tokens_used,
                cost=response.cost
            )
        
        # Step 5: Return response
        return response
    
    @abstractmethod
    async def _execute_impl(self, request: AIRequest) -> AIResponse:
        """
        Provider-specific execution logic.
        
        Subclasses implement this instead of execute().
        
        Args:
            request: Standardized AI request (with memory loaded)
            
        Returns:
            Standardized AI response
        """
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider metadata for observability."""
        return {
            "provider": self.provider.value,
            "config": {k: v for k, v in self.config.items() if k not in ['api_key', 'secret']},
            "guardrails_enabled": self.enable_guardrails,
            "memory_enabled": self.enable_memory,
        }
    
    async def _get_guardrails(self):
        """Lazy load guardrails."""
        if self._guardrails is None:
            from backend.ai.guardrails import get_guardrails
            from backend.core.redis import get_redis
            
            redis = await get_redis()
            self._guardrails = get_guardrails(redis)
        
        return self._guardrails
    
    async def _get_memory_loader(self):
        """Lazy load memory loader."""
        if self._memory_loader is None:
            from backend.ai.memory import get_memory_loader
            from backend.core.redis import get_redis
            from backend.core.database import get_db
            
            db = await get_db()
            redis = await get_redis()
            self._memory_loader = get_memory_loader(db, redis)
        
        return self._memory_loader


class AIOrchestrationError(Exception):
    """Base exception for AI orchestration errors."""
    pass


class AIProviderUnavailableError(AIOrchestrationError):
    """AI provider is unavailable or unhealthy."""
    pass


class AIRequestValidationError(AIOrchestrationError):
    """AI request is invalid."""
    pass

