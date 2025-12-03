"""
LangChain implementation of AI Orchestrator.

This wraps existing LangChainOrchestrator with the standard interface.
NO business logic changes - pure adapter pattern.
"""

from typing import Optional, Dict, Any
import time
import uuid

from backend.ai.orchestrators.base import (
    BaseAIOrchestrator,
    AIProvider,
    AIRequest,
    AIResponse,
    AITaskType,
    AIProviderUnavailableError,
)
from backend.ai.orchestrators.langchain.orchestrator import LangChainOrchestrator


class LangChainOrchestratorAdapter(BaseAIOrchestrator):
    """
    Adapter that wraps LangChainOrchestrator with BaseAIOrchestrator interface.
    
    This allows existing code to continue working while providing standard interface.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        **kwargs
    ):
        super().__init__(provider=AIProvider.OPENAI, api_key=api_key, model_name=model_name, temperature=temperature)
        
        # Wrap existing LangChainOrchestrator (NO changes to it)
        self._langchain = LangChainOrchestrator(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
        )
    
    async def _execute_impl(self, request: AIRequest) -> AIResponse:
        """
        Execute AI request using LangChain.
        
        This translates standard AIRequest → LangChain call → standard AIResponse.
        NOTE: This method is called by BaseAIOrchestrator.execute() AFTER
        guardrails and memory loading.
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Route based on task type
            if request.task_type == AITaskType.TEXT_GENERATION:
                result = await self._execute_text_generation(request)
            elif request.task_type == AITaskType.CLASSIFICATION:
                result = await self._execute_classification(request)
            elif request.task_type == AITaskType.SCORING:
                result = await self._execute_scoring(request)
            elif request.task_type == AITaskType.RECOMMENDATION:
                result = await self._execute_recommendation(request)
            elif request.task_type == AITaskType.CHAT:
                result = await self._execute_chat(request)
            else:
                # Default: text generation
                result = await self._execute_text_generation(request)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Calculate cost (rough estimate for GPT-4)
            # GPT-4: $0.03 per 1K input tokens, $0.06 per 1K output tokens
            # Approximation: 4 chars = 1 token
            input_tokens = len(request.prompt) // 4
            output_tokens = len(str(result)) // 4
            cost = (input_tokens / 1000 * 0.03) + (output_tokens / 1000 * 0.06)
            
            return AIResponse(
                result=result,
                provider=self.provider,
                model=request.model or self._langchain.model_name,
                task_type=request.task_type,
                latency_ms=latency_ms,
                request_id=request_id,
                tokens_used=input_tokens + output_tokens,
                cost=cost,
            )
        
        except Exception as e:
            raise AIProviderUnavailableError(f"LangChain execution failed: {e}") from e
    
    async def _execute_text_generation(self, request: AIRequest) -> str:
        """Execute text generation using LangChain."""
        chat_model = self._langchain.get_chat_model(
            model_name=request.model,
            temperature=request.temperature,
        )
        
        # Simple text generation
        response = chat_model.invoke(request.prompt)
        return response.content
    
    async def _execute_classification(self, request: AIRequest) -> Dict[str, Any]:
        """Execute classification using LangChain."""
        # Use existing LangChain with classification prompt
        chat_model = self._langchain.get_chat_model(
            model_name=request.model,
            temperature=0.0,  # Classification needs deterministic results
        )
        
        response = chat_model.invoke(request.prompt)
        
        # Parse classification result
        # In real implementation, use structured output
        return {
            "class": response.content,
            "confidence": None,  # LangChain doesn't expose probabilities
        }
    
    async def _execute_scoring(self, request: AIRequest) -> Dict[str, Any]:
        """Execute scoring using LangChain."""
        chat_model = self._langchain.get_chat_model(
            model_name=request.model,
            temperature=0.0,  # Scoring needs consistency
        )
        
        response = chat_model.invoke(request.prompt)
        
        # Parse score from response
        # In real implementation, use structured output or function calling
        try:
            score = float(response.content.strip())
            return {"score": score, "reasoning": None}
        except ValueError:
            return {"score": None, "reasoning": response.content}
    
    async def _execute_recommendation(self, request: AIRequest) -> Dict[str, Any]:
        """Execute recommendation using LangChain."""
        chat_model = self._langchain.get_chat_model(
            model_name=request.model,
            temperature=request.temperature or 0.5,
        )
        
        response = chat_model.invoke(request.prompt)
        
        return {
            "recommendation": response.content,
            "reasoning": request.context.get("reasoning") if request.context else None,
        }
    
    async def _execute_chat(self, request: AIRequest) -> str:
        """
        Execute chat using LangChain with memory support.
        
        Uses conversation_history from request if available.
        """
        chat_model = self._langchain.get_chat_model(
            model_name=request.model,
            temperature=request.temperature or 0.7,
        )
        
        # Build messages with history
        messages = []
        
        # Add conversation history
        for msg in request.conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                from langchain_core.messages import SystemMessage
                messages.append(SystemMessage(content=content))
            elif role == "assistant":
                from langchain_core.messages import AIMessage
                messages.append(AIMessage(content=content))
            else:
                from langchain_core.messages import HumanMessage
                messages.append(HumanMessage(content=content))
        
        # Add current message
        from langchain_core.messages import HumanMessage
        messages.append(HumanMessage(content=request.prompt))
        
        # Add user context as system message if available
        if request.user_context:
            from langchain_core.messages import SystemMessage
            context_summary = request.user_context.get("summary", "")
            if context_summary:
                messages.insert(0, SystemMessage(content=f"User context: {context_summary}"))
        
        response = chat_model.invoke(messages)
        return response.content
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            # Simple health check
            chat_model = self._langchain.get_chat_model()
            response = chat_model.invoke("ping")
            return True
        except Exception:
            return False
