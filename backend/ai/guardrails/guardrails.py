"""
AI Guardrails

Safety, rate limiting, and cost control for AI operations.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass
class GuardrailViolation:
    """Guardrail violation information."""
    
    type: str  # rate_limit, cost_limit, content_filter
    message: str
    details: Dict[str, Any]


class AIGuardrails:
    """
    Enforce safety and cost limits for AI operations.
    
    Features:
    - Rate limiting (requests per user per hour)
    - Cost tracking (token usage and monthly budgets)
    - Content filtering (harmful/inappropriate inputs)
    - Abuse detection (repeated violations)
    
    Usage:
        guardrails = AIGuardrails(redis)
        
        # Before AI call
        violation = await guardrails.check_request(
            user_id=user_id,
            tokens_estimate=1000,
            prompt=user_message
        )
        
        if violation:
            raise HTTPException(429, violation.message)
        
        # After AI call
        await guardrails.record_usage(
            user_id=user_id,
            tokens_used=response.tokens_used,
            cost=response.cost
        )
    """
    
    # Default limits
    DEFAULT_RATE_LIMIT = 100  # requests per hour
    DEFAULT_MONTHLY_BUDGET = 50.0  # USD per user per month
    DEFAULT_MAX_TOKENS_PER_REQUEST = 4000
    
    # Abuse thresholds
    ABUSE_THRESHOLD = 10  # violations per hour
    ABUSE_BAN_DURATION = 3600  # 1 hour ban
    
    def __init__(self, redis: Optional[Redis] = None):
        self.redis = redis
        
        # Content filters (keywords to block)
        self._banned_keywords = {
            # Add harmful content keywords here
            "hack", "exploit", "bypass", "jailbreak",
        }
    
    async def check_request(
        self,
        user_id: UUID,
        tokens_estimate: int = 1000,
        prompt: Optional[str] = None
    ) -> Optional[GuardrailViolation]:
        """
        Check if request passes guardrails.
        
        Args:
            user_id: User UUID
            tokens_estimate: Estimated tokens for request
            prompt: User prompt (optional, for content filtering)
            
        Returns:
            GuardrailViolation if failed, None if passed
        """
        # Check if user is banned
        if await self._is_banned(user_id):
            return GuardrailViolation(
                type="abuse_ban",
                message="Too many violations. Temporarily banned from AI features.",
                details={"ban_expires_in_seconds": await self._get_ban_ttl(user_id)}
            )
        
        # Check rate limit
        rate_violation = await self._check_rate_limit(user_id)
        if rate_violation:
            await self._record_violation(user_id, "rate_limit")
            return rate_violation
        
        # Check token limit
        if tokens_estimate > self.DEFAULT_MAX_TOKENS_PER_REQUEST:
            return GuardrailViolation(
                type="token_limit",
                message=f"Request too large. Max {self.DEFAULT_MAX_TOKENS_PER_REQUEST} tokens.",
                details={"tokens_estimate": tokens_estimate}
            )
        
        # Check monthly cost limit
        cost_violation = await self._check_cost_limit(user_id, tokens_estimate)
        if cost_violation:
            await self._record_violation(user_id, "cost_limit")
            return cost_violation
        
        # Check content filter
        if prompt:
            content_violation = await self._check_content(prompt)
            if content_violation:
                await self._record_violation(user_id, "content_filter")
                return content_violation
        
        return None
    
    async def record_usage(
        self,
        user_id: UUID,
        tokens_used: int,
        cost: float = 0.0
    ) -> None:
        """
        Record AI usage for rate limiting and cost tracking.
        
        Args:
            user_id: User UUID
            tokens_used: Actual tokens used
            cost: Actual cost in USD
        """
        if not self.redis:
            return
        
        try:
            # Increment request count (TTL 1 hour)
            rate_key = f"ai:rate:{user_id}"
            await self.redis.incr(rate_key)
            await self.redis.expire(rate_key, 3600)
            
            # Track monthly cost
            now = datetime.utcnow()
            month_key = f"ai:cost:{user_id}:{now.year}-{now.month:02d}"
            
            await self.redis.incrbyfloat(month_key, cost)
            # Expire at end of month (30 days)
            await self.redis.expire(month_key, 30 * 24 * 3600)
            
            # Track monthly tokens
            tokens_key = f"ai:tokens:{user_id}:{now.year}-{now.month:02d}"
            await self.redis.incrby(tokens_key, tokens_used)
            await self.redis.expire(tokens_key, 30 * 24 * 3600)
        
        except Exception as e:
            logger.error(f"Failed to record AI usage: {e}")
    
    async def get_usage_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get usage statistics for user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Usage stats (requests, tokens, cost)
        """
        if not self.redis:
            return {}
        
        try:
            now = datetime.utcnow()
            month_key_prefix = f"ai:cost:{user_id}:{now.year}-{now.month:02d}"
            
            # Get current hour rate
            rate_key = f"ai:rate:{user_id}"
            requests_this_hour = await self.redis.get(rate_key) or 0
            
            # Get monthly cost
            cost_key = f"ai:cost:{user_id}:{now.year}-{now.month:02d}"
            monthly_cost = await self.redis.get(cost_key) or 0.0
            
            # Get monthly tokens
            tokens_key = f"ai:tokens:{user_id}:{now.year}-{now.month:02d}"
            monthly_tokens = await self.redis.get(tokens_key) or 0
            
            return {
                "requests_this_hour": int(requests_this_hour),
                "rate_limit": self.DEFAULT_RATE_LIMIT,
                "monthly_cost": float(monthly_cost),
                "monthly_budget": self.DEFAULT_MONTHLY_BUDGET,
                "monthly_tokens": int(monthly_tokens),
            }
        
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}
    
    async def _check_rate_limit(self, user_id: UUID) -> Optional[GuardrailViolation]:
        """Check rate limit."""
        if not self.redis:
            return None
        
        try:
            rate_key = f"ai:rate:{user_id}"
            count = await self.redis.get(rate_key)
            
            if count and int(count) >= self.DEFAULT_RATE_LIMIT:
                ttl = await self.redis.ttl(rate_key)
                return GuardrailViolation(
                    type="rate_limit",
                    message=f"Rate limit exceeded. Try again in {ttl} seconds.",
                    details={
                        "requests_this_hour": int(count),
                        "limit": self.DEFAULT_RATE_LIMIT,
                        "reset_in_seconds": ttl,
                    }
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return None
    
    async def _check_cost_limit(
        self,
        user_id: UUID,
        tokens_estimate: int
    ) -> Optional[GuardrailViolation]:
        """Check monthly cost limit."""
        if not self.redis:
            return None
        
        try:
            now = datetime.utcnow()
            cost_key = f"ai:cost:{user_id}:{now.year}-{now.month:02d}"
            monthly_cost = await self.redis.get(cost_key) or 0.0
            monthly_cost = float(monthly_cost)
            
            # Estimate additional cost (GPT-4: ~$0.03/1K tokens)
            estimated_cost = (tokens_estimate / 1000) * 0.03
            
            if monthly_cost + estimated_cost > self.DEFAULT_MONTHLY_BUDGET:
                return GuardrailViolation(
                    type="cost_limit",
                    message=f"Monthly budget exceeded. Used ${monthly_cost:.2f} of ${self.DEFAULT_MONTHLY_BUDGET:.2f}.",
                    details={
                        "monthly_cost": monthly_cost,
                        "budget": self.DEFAULT_MONTHLY_BUDGET,
                        "estimated_additional_cost": estimated_cost,
                    }
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to check cost limit: {e}")
            return None
    
    async def _check_content(self, prompt: str) -> Optional[GuardrailViolation]:
        """Check content for harmful keywords."""
        prompt_lower = prompt.lower()
        
        for keyword in self._banned_keywords:
            if keyword in prompt_lower:
                return GuardrailViolation(
                    type="content_filter",
                    message="Request contains inappropriate content.",
                    details={"keyword": keyword}
                )
        
        return None
    
    async def _record_violation(self, user_id: UUID, violation_type: str) -> None:
        """Record guardrail violation."""
        if not self.redis:
            return
        
        try:
            violations_key = f"ai:violations:{user_id}"
            count = await self.redis.incr(violations_key)
            await self.redis.expire(violations_key, 3600)  # 1 hour
            
            # Ban if too many violations
            if count >= self.ABUSE_THRESHOLD:
                ban_key = f"ai:ban:{user_id}"
                await self.redis.setex(ban_key, self.ABUSE_BAN_DURATION, "1")
                logger.warning(f"User {user_id} banned for {self.ABUSE_BAN_DURATION}s due to abuse")
        
        except Exception as e:
            logger.error(f"Failed to record violation: {e}")
    
    async def _is_banned(self, user_id: UUID) -> bool:
        """Check if user is banned."""
        if not self.redis:
            return False
        
        try:
            ban_key = f"ai:ban:{user_id}"
            return await self.redis.exists(ban_key) > 0
        
        except Exception as e:
            logger.error(f"Failed to check ban status: {e}")
            return False
    
    async def _get_ban_ttl(self, user_id: UUID) -> int:
        """Get ban TTL in seconds."""
        if not self.redis:
            return 0
        
        try:
            ban_key = f"ai:ban:{user_id}"
            return await self.redis.ttl(ban_key)
        
        except Exception as e:
            logger.error(f"Failed to get ban TTL: {e}")
            return 0


# Singleton
_guardrails: Optional[AIGuardrails] = None


def get_guardrails(redis: Optional[Redis] = None) -> AIGuardrails:
    """
    Get guardrails instance.
    
    Args:
        redis: Redis client (optional)
        
    Returns:
        AIGuardrails instance
    """
    global _guardrails
    if _guardrails is None:
        _guardrails = AIGuardrails(redis)
    return _guardrails
