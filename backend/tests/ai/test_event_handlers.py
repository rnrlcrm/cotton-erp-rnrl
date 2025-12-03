"""
Test AI Event Handlers

Tests for vector sync event handlers.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock
from backend.ai.events.handlers import (
    handle_requirement_created,
    handle_availability_created,
    register_ai_event_handlers,
)


@pytest.mark.asyncio
async def test_handle_requirement_created(db_session, mocker):
    """Test requirement.created event handler."""
    from backend.core.events.base import BaseEvent
    
    # Mock EmbeddingSyncJob
    mock_job = mocker.patch("backend.ai.events.handlers.EmbeddingSyncJob")
    mock_instance = mock_job.return_value
    mock_instance.handle_requirement_event = AsyncMock()
    
    # Create event
    event = BaseEvent(
        event_type="requirement.created",
        aggregate_id=uuid4(),
        aggregate_type="requirement",
        version=1,
        payload={},
    )
    
    # Handle event
    await handle_requirement_created(event, db_session)
    
    # Verify job was called
    mock_instance.handle_requirement_event.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_handle_availability_created(db_session, mocker):
    """Test availability.created event handler."""
    from backend.core.events.base import BaseEvent
    
    # Mock EmbeddingSyncJob
    mock_job = mocker.patch("backend.ai.events.handlers.EmbeddingSyncJob")
    mock_instance = mock_job.return_value
    mock_instance.handle_availability_event = AsyncMock()
    
    # Create event
    event = BaseEvent(
        event_type="availability.created",
        aggregate_id=uuid4(),
        aggregate_type="availability",
        version=1,
        payload={},
    )
    
    # Handle event
    await handle_availability_created(event, db_session)
    
    # Verify job was called
    mock_instance.handle_availability_event.assert_called_once_with(event)


def test_register_ai_event_handlers():
    """Test event handler registration."""
    mock_event_bus = Mock()
    mock_event_bus.subscribe = Mock()
    
    # Register handlers
    register_ai_event_handlers(mock_event_bus)
    
    # Verify subscriptions
    assert mock_event_bus.subscribe.call_count == 4
    
    # Check event types
    calls = mock_event_bus.subscribe.call_args_list
    event_types = [call[0][0] for call in calls]
    
    assert "requirement.created" in event_types
    assert "requirement.updated" in event_types
    assert "availability.created" in event_types
    assert "availability.updated" in event_types
