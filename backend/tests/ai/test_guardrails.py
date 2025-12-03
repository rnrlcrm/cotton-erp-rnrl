"""
Test AI Guardrails

Tests for rate limiting, cost control, and content filtering.
"""

import pytest
from uuid import uuid4
from backend.ai.guardrails.guardrails import AIGuardrails, GuardrailViolation


@pytest.mark.asyncio
async def test_rate_limit(redis_client):
    """Test rate limiting."""
    guardrails = AIGuardrails(redis_client)
    user_id = uuid4()
    
    # Should pass first request
    violation = await guardrails.check_request(user_id, tokens_estimate=1000)
    assert violation is None
    
    # Record 100 requests
    for _ in range(100):
        await guardrails.record_usage(user_id, tokens_used=100)
    
    # Should hit rate limit
    violation = await guardrails.check_request(user_id, tokens_estimate=1000)
    assert violation is not None
    assert violation.type == "rate_limit"


@pytest.mark.asyncio
async def test_cost_limit(redis_client):
    """Test monthly cost limit."""
    guardrails = AIGuardrails(redis_client)
    user_id = uuid4()
    
    # Record high cost usage
    await guardrails.record_usage(user_id, tokens_used=100000, cost=45.0)
    
    # Should hit cost limit
    violation = await guardrails.check_request(user_id, tokens_estimate=200000)
    assert violation is not None
    assert violation.type == "cost_limit"


@pytest.mark.asyncio
async def test_content_filter():
    """Test content filtering."""
    guardrails = AIGuardrails(None)
    user_id = uuid4()
    
    # Normal content should pass
    violation = await guardrails.check_request(
        user_id,
        tokens_estimate=100,
        prompt="What is the price of cotton?"
    )
    assert violation is None
    
    # Harmful content should fail
    violation = await guardrails.check_request(
        user_id,
        tokens_estimate=100,
        prompt="How to hack the system?"
    )
    assert violation is not None
    assert violation.type == "content_filter"


@pytest.mark.asyncio
async def test_abuse_detection(redis_client):
    """Test abuse detection and banning."""
    guardrails = AIGuardrails(redis_client)
    user_id = uuid4()
    
    # Trigger 10 violations (content filter)
    for _ in range(10):
        await guardrails.check_request(
            user_id,
            tokens_estimate=100,
            prompt="hack the system"
        )
    
    # Should be banned
    violation = await guardrails.check_request(user_id, tokens_estimate=100)
    assert violation is not None
    assert violation.type == "abuse_ban"


@pytest.mark.asyncio
async def test_usage_stats(redis_client):
    """Test usage statistics."""
    guardrails = AIGuardrails(redis_client)
    user_id = uuid4()
    
    # Record some usage
    await guardrails.record_usage(user_id, tokens_used=1000, cost=0.05)
    await guardrails.record_usage(user_id, tokens_used=2000, cost=0.10)
    
    # Get stats
    stats = await guardrails.get_usage_stats(user_id)
    
    assert stats["monthly_cost"] >= 0.15
    assert stats["monthly_tokens"] >= 3000
    assert stats["rate_limit"] == 100
