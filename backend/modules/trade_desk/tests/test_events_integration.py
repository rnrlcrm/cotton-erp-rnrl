"""
Integration Tests: Domain Events

Tests event creation, serialization, all to_dict() methods.
Target Coverage: 100% of events.py

Test Categories:
1. MatchFoundEvent - Event creation and serialization
2. MatchRejectedEvent - Rejection event handling
3. MatchAllocatedEvent - Allocation event handling
4. Event serialization - to_dict() methods
5. Event metadata - Timestamps and identifiers
"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4, UUID
from typing import Dict, Any

from backend.modules.trade_desk.matching.events import (
    MatchFoundEvent,
    MatchRejectedEvent,
    MatchAllocatedEvent
)


# ============================================================================
# TEST CATEGORY 1: MatchFoundEvent
# ============================================================================

class TestMatchFoundEvent:
    """Test MatchFoundEvent creation and serialization."""
    
    def test_creates_match_found_event_with_all_fields(self):
        """Should create event with complete match details."""
        # Arrange
        requirement_id = uuid4()
        availability_id = uuid4()
        score = 0.85
        breakdown = {
            "quality_score": 0.9,
            "price_score": 0.8,
            "delivery_score": 0.85,
            "risk_score": 1.0
        }
        
        # Act
        event = MatchFoundEvent(
            requirement_id=requirement_id,
            availability_id=availability_id,
            match_score=score,
            score_breakdown=breakdown,
            risk_status="PASS"
        )
        
        # Assert
        assert event.requirement_id == requirement_id
        assert event.availability_id == availability_id
        assert event.match_score == score
        assert event.score_breakdown == breakdown
        assert event.risk_status == "PASS"
        assert isinstance(event.matched_at, datetime)
        assert isinstance(event.event_id, UUID)
    
    def test_to_dict_serializes_all_fields(self):
        """to_dict() should serialize all event fields."""
        # Arrange
        event = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.85,
            score_breakdown={
                "quality_score": 0.9,
                "price_score": 0.8,
                "delivery_score": 0.85,
                "risk_score": 1.0
            },
            risk_status="PASS"
        )
        
        # Act
        event_dict = event.to_dict()
        
        # Assert
        assert "event_id" in event_dict
        assert "event_type" in event_dict
        assert event_dict["event_type"] == "match.found"
        assert "requirement_id" in event_dict
        assert "availability_id" in event_dict
        assert "match_score" in event_dict
        assert "score_breakdown" in event_dict
        assert "risk_status" in event_dict
        assert "matched_at" in event_dict
        
        # Verify UUIDs serialized as strings
        assert isinstance(event_dict["requirement_id"], str)
        assert isinstance(event_dict["availability_id"], str)
        assert isinstance(event_dict["event_id"], str)
        
        # Verify datetime serialized as ISO string
        assert isinstance(event_dict["matched_at"], str)
    
    def test_handles_warn_risk_status(self):
        """Should handle WARN risk status with penalty flag."""
        # Arrange & Act
        event = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.75,
            score_breakdown={},
            risk_status="WARN",
            warn_penalty_applied=True
        )
        
        # Assert
        assert event.risk_status == "WARN"
        assert event.warn_penalty_applied is True
        
        event_dict = event.to_dict()
        assert event_dict["warn_penalty_applied"] is True
    
    def test_includes_optional_match_details(self):
        """Should include optional match details in serialization."""
        # Arrange
        match_details = {
            "commodity": "COTTON",
            "quantity": "100.000",
            "price": "48000.00"
        }
        
        event = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.85,
            score_breakdown={},
            risk_status="PASS",
            match_details=match_details
        )
        
        # Act
        event_dict = event.to_dict()
        
        # Assert
        assert "match_details" in event_dict
        assert event_dict["match_details"] == match_details


# ============================================================================
# TEST CATEGORY 2: MatchRejectedEvent
# ============================================================================

class TestMatchRejectedEvent:
    """Test MatchRejectedEvent creation and serialization."""
    
    def test_creates_match_rejected_event(self):
        """Should create rejection event with reason."""
        # Arrange
        requirement_id = uuid4()
        availability_id = uuid4()
        reason = "Price too high"
        
        # Act
        event = MatchRejectedEvent(
            requirement_id=requirement_id,
            availability_id=availability_id,
            rejection_reason=reason
        )
        
        # Assert
        assert event.requirement_id == requirement_id
        assert event.availability_id == availability_id
        assert event.rejection_reason == reason
        assert isinstance(event.rejected_at, datetime)
        assert isinstance(event.event_id, UUID)
    
    def test_to_dict_includes_rejection_details(self):
        """to_dict() should include rejection reason and details."""
        # Arrange
        rejection_details = {
            "failed_checks": ["price_validation", "quantity_validation"],
            "max_price": "55000.00",
            "offered_price": "60000.00"
        }
        
        event = MatchRejectedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            rejection_reason="Price above maximum",
            rejection_details=rejection_details
        )
        
        # Act
        event_dict = event.to_dict()
        
        # Assert
        assert event_dict["event_type"] == "match.rejected"
        assert event_dict["rejection_reason"] == "Price above maximum"
        assert event_dict["rejection_details"] == rejection_details
    
    def test_handles_risk_fail_rejection(self):
        """Should handle risk FAIL rejection."""
        # Arrange & Act
        event = MatchRejectedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            rejection_reason="Risk status FAIL",
            rejection_details={
                "risk_status": "FAIL",
                "risk_score": 30,
                "flags": ["high_credit_risk"]
            }
        )
        
        # Assert
        event_dict = event.to_dict()
        assert "Risk status FAIL" in event_dict["rejection_reason"]
        assert event_dict["rejection_details"]["risk_status"] == "FAIL"
    
    def test_handles_location_mismatch_rejection(self):
        """Should handle location filter rejection."""
        # Arrange & Act
        event = MatchRejectedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            rejection_reason="Location mismatch",
            rejection_details={
                "buyer_location": "Mumbai",
                "seller_location": "Delhi",
                "cross_state_blocked": True
            }
        )
        
        # Assert
        event_dict = event.to_dict()
        assert event_dict["rejection_reason"] == "Location mismatch"
        assert event_dict["rejection_details"]["cross_state_blocked"] is True


# ============================================================================
# TEST CATEGORY 3: MatchAllocatedEvent
# ============================================================================

class TestMatchAllocatedEvent:
    """Test MatchAllocatedEvent creation and serialization."""
    
    def test_creates_match_allocated_event(self):
        """Should create allocation event with quantity details."""
        # Arrange
        requirement_id = uuid4()
        availability_id = uuid4()
        allocated_qty = Decimal("75.000")
        
        # Act
        event = MatchAllocatedEvent(
            requirement_id=requirement_id,
            availability_id=availability_id,
            allocated_quantity=allocated_qty
        )
        
        # Assert
        assert event.requirement_id == requirement_id
        assert event.availability_id == availability_id
        assert event.allocated_quantity == allocated_qty
        assert isinstance(event.allocated_at, datetime)
        assert isinstance(event.event_id, UUID)
    
    def test_to_dict_includes_allocation_details(self):
        """to_dict() should include allocation quantity and metadata."""
        # Arrange
        event = MatchAllocatedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            allocated_quantity=Decimal("75.000"),
            remaining_requirement=Decimal("25.000"),
            remaining_availability=Decimal("50.000")
        )
        
        # Act
        event_dict = event.to_dict()
        
        # Assert
        assert event_dict["event_type"] == "match.allocated"
        assert "allocated_quantity" in event_dict
        assert "remaining_requirement" in event_dict
        assert "remaining_availability" in event_dict
        
        # Verify Decimal serialized as string
        assert isinstance(event_dict["allocated_quantity"], str)
    
    def test_handles_full_allocation(self):
        """Should handle full requirement allocation."""
        # Arrange & Act
        event = MatchAllocatedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            allocated_quantity=Decimal("100.000"),
            remaining_requirement=Decimal("0.000"),
            remaining_availability=Decimal("50.000"),
            is_full_allocation=True
        )
        
        # Assert
        event_dict = event.to_dict()
        assert event_dict["is_full_allocation"] is True
        assert event_dict["remaining_requirement"] == "0.000"
    
    def test_handles_partial_allocation(self):
        """Should handle partial allocation."""
        # Arrange & Act
        event = MatchAllocatedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            allocated_quantity=Decimal("60.000"),
            remaining_requirement=Decimal("40.000"),
            remaining_availability=Decimal("90.000"),
            is_full_allocation=False
        )
        
        # Assert
        event_dict = event.to_dict()
        assert event_dict["is_full_allocation"] is False
        assert event_dict["allocated_quantity"] == "60.000"
    
    def test_includes_match_score_in_allocation(self):
        """Should include match score in allocation event."""
        # Arrange
        event = MatchAllocatedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            allocated_quantity=Decimal("75.000"),
            match_score=0.87
        )
        
        # Act
        event_dict = event.to_dict()
        
        # Assert
        assert "match_score" in event_dict
        assert event_dict["match_score"] == 0.87


# ============================================================================
# TEST CATEGORY 4: Event Serialization Edge Cases
# ============================================================================

class TestEventSerialization:
    """Test edge cases in event serialization."""
    
    def test_handles_none_values_in_optional_fields(self):
        """Should handle None values in optional fields."""
        # Arrange
        event = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.85,
            score_breakdown={},
            risk_status="PASS",
            match_details=None,
            warn_penalty_applied=None
        )
        
        # Act
        event_dict = event.to_dict()
        
        # Assert
        assert "match_details" in event_dict or event_dict.get("match_details") is None
        # Should not crash
    
    def test_handles_empty_score_breakdown(self):
        """Should handle empty score breakdown."""
        # Arrange
        event = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.85,
            score_breakdown={},
            risk_status="PASS"
        )
        
        # Act
        event_dict = event.to_dict()
        
        # Assert
        assert "score_breakdown" in event_dict
        assert event_dict["score_breakdown"] == {}
    
    def test_serializes_nested_dictionaries(self):
        """Should properly serialize nested dictionaries."""
        # Arrange
        complex_details = {
            "risk_assessment": {
                "buyer_rating": 4.5,
                "seller_rating": 4.8,
                "flags": ["new_buyer"]
            },
            "pricing": {
                "base_price": "48000.00",
                "expected_price": "50000.00",
                "discount_percent": 4.0
            }
        }
        
        event = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.85,
            score_breakdown={},
            risk_status="PASS",
            match_details=complex_details
        )
        
        # Act
        event_dict = event.to_dict()
        
        # Assert
        assert event_dict["match_details"]["risk_assessment"]["flags"] == ["new_buyer"]
        assert event_dict["match_details"]["pricing"]["discount_percent"] == 4.0


# ============================================================================
# TEST CATEGORY 5: Event Metadata
# ============================================================================

class TestEventMetadata:
    """Test event metadata and identifiers."""
    
    def test_generates_unique_event_ids(self):
        """Each event should have unique event_id."""
        # Arrange & Act
        event1 = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.85,
            score_breakdown={},
            risk_status="PASS"
        )
        
        event2 = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.75,
            score_breakdown={},
            risk_status="PASS"
        )
        
        # Assert
        assert event1.event_id != event2.event_id
    
    def test_timestamps_are_recent(self):
        """Event timestamps should be recent (within 1 second)."""
        # Arrange & Act
        before = datetime.utcnow()
        event = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.85,
            score_breakdown={},
            risk_status="PASS"
        )
        after = datetime.utcnow()
        
        # Assert
        assert before <= event.matched_at <= after
    
    def test_event_type_constants(self):
        """Event types should be correct constants."""
        # Arrange & Act
        found_event = MatchFoundEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score=0.85,
            score_breakdown={},
            risk_status="PASS"
        )
        
        rejected_event = MatchRejectedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            rejection_reason="Test"
        )
        
        allocated_event = MatchAllocatedEvent(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            allocated_quantity=Decimal("75.000")
        )
        
        # Assert
        assert found_event.to_dict()["event_type"] == "match.found"
        assert rejected_event.to_dict()["event_type"] == "match.rejected"
        assert allocated_event.to_dict()["event_type"] == "match.allocated"
    
    def test_all_events_have_required_metadata(self):
        """All events should have event_id and timestamp."""
        # Arrange & Act
        events = [
            MatchFoundEvent(
                requirement_id=uuid4(),
                availability_id=uuid4(),
                match_score=0.85,
                score_breakdown={},
                risk_status="PASS"
            ),
            MatchRejectedEvent(
                requirement_id=uuid4(),
                availability_id=uuid4(),
                rejection_reason="Test"
            ),
            MatchAllocatedEvent(
                requirement_id=uuid4(),
                availability_id=uuid4(),
                allocated_quantity=Decimal("75.000")
            )
        ]
        
        # Assert
        for event in events:
            event_dict = event.to_dict()
            assert "event_id" in event_dict
            assert "event_type" in event_dict
            assert isinstance(UUID(event_dict["event_id"]), UUID)
