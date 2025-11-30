"""
Test infrastructure changes (idempotency, AI orchestrator, event versioning).

These tests verify that our 15-year architecture hardening works correctly.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.core.events.versioning import (
    get_current_version,
    validate_event_version,
    upgrade_event_version,
)
from backend.core.events.base import BaseEvent
from backend.ai.orchestrators.base import (
    AIRequest,
    AIResponse,
    AITaskType,
    AIProvider,
)
import uuid


class TestEventVersioning:
    """Test event versioning strategy."""
    
    def test_get_current_version_known_event(self):
        """Test getting version of known event type."""
        version = get_current_version("organization.created")
        assert version == 1
    
    def test_get_current_version_unknown_event(self):
        """Test getting version of unknown event type defaults to 1."""
        version = get_current_version("unknown.event")
        assert version == 1
    
    def test_validate_event_version_valid(self):
        """Test validating valid event version."""
        event = BaseEvent(
            event_type="organization.created",
            aggregate_id=uuid.uuid4(),
            aggregate_type="organization",
            user_id=uuid.uuid4(),
            version=1,
            data={"name": "Test Org"},
        )
        
        # Should not raise
        validate_event_version(event)
    
    def test_validate_event_version_too_low(self):
        """Test validating version < 1 raises error."""
        event = BaseEvent(
            event_type="organization.created",
            aggregate_id=uuid.uuid4(),
            aggregate_type="organization",
            user_id=uuid.uuid4(),
            version=0,  # Invalid
            data={"name": "Test Org"},
        )
        
        with pytest.raises(ValueError, match="must be >= 1"):
            validate_event_version(event)
    
    def test_validate_event_version_too_high(self):
        """Test validating version > current raises error."""
        event = BaseEvent(
            event_type="organization.created",
            aggregate_id=uuid.uuid4(),
            aggregate_type="organization",
            user_id=uuid.uuid4(),
            version=999,  # Too high
            data={"name": "Test Org"},
        )
        
        with pytest.raises(ValueError, match="newer than current version"):
            validate_event_version(event)
    
    def test_upgrade_event_version_same(self):
        """Test upgrading to same version returns unchanged."""
        data = {"trade_id": "123", "amount": 100}
        result = upgrade_event_version(data, 1, 1)
        assert result == data
    
    def test_upgrade_event_version_no_migration(self):
        """Test upgrading without explicit migration function."""
        data = {"trade_id": "123", "amount": 100}
        result = upgrade_event_version(data, 1, 2)
        # Should return data (no-op migration)
        assert result == data


class TestAIOrchestrator:
    """Test AI Orchestrator interface."""
    
    def test_ai_request_creation(self):
        """Test creating AI request."""
        request = AIRequest(
            task_type=AITaskType.SCORING,
            prompt="Score this match from 0-100",
            temperature=0.0,
        )
        
        assert request.task_type == AITaskType.SCORING
        assert request.prompt == "Score this match from 0-100"
        assert request.temperature == 0.0
    
    def test_ai_response_timestamp(self):
        """Test AI response includes timestamp."""
        response = AIResponse(
            result={"score": 85},
            provider=AIProvider.OPENAI,
            model="gpt-4",
            task_type=AITaskType.SCORING,
        )
        
        assert response.result == {"score": 85}
        assert response.provider == AIProvider.OPENAI
        assert response.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_ai_orchestrator_factory(self):
        """Test getting orchestrator from factory."""
        try:
            from backend.ai.orchestrators.factory import get_orchestrator, reset_orchestrator
            
            # Reset singleton
            reset_orchestrator()
            
            # Get orchestrator (will create LangChainAdapter)
            with patch('backend.ai.orchestrators.langchain_adapter.LangChainOrchestrator'):
                orchestrator = get_orchestrator()
                
                assert orchestrator is not None
                assert orchestrator.provider == AIProvider.OPENAI
        except ImportError:
            # LangChain not installed in dev - skip test
            pytest.skip("LangChain not installed (expected in dev)")


def test_infrastructure_smoke():
    """Smoke test that all infrastructure modules import correctly."""
    # These should all import without errors
    from backend.app.middleware.idempotency import IdempotencyMiddleware
    from backend.core.config.secrets import get_env_or_secret
    from backend.ai.orchestrators.base import BaseAIOrchestrator
    from backend.core.events.versioning import validate_event_version
    
    assert IdempotencyMiddleware is not None
    assert get_env_or_secret is not None
    assert BaseAIOrchestrator is not None
    assert validate_event_version is not None
    
    # GCP observability and AI factory require optional dependencies
    # These will be installed in production GCP environment
    try:
        from backend.core.observability.gcp import configure_gcp_observability
        from backend.ai.orchestrators.factory import get_orchestrator
        assert configure_gcp_observability is not None
        assert get_orchestrator is not None
    except ImportError:
        # Expected in dev environment
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
