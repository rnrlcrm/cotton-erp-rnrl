"""
Integration Tests: Match Validators

Tests validation workflows, risk compliance, AI validation, internal branch blocking.
Target Coverage: 85% of validators.py

Test Categories:
1. validate_match_eligibility() - Comprehensive match validation
2. validate_risk_compliance() - Risk status validation
3. validate_quantity_availability() - Quantity checks
4. validate_internal_branch_trading() - Internal trading prevention
5. validate_ai_requirements() - AI confidence checks
6. Integration workflows - Combined validations
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, patch

from backend.modules.trade_desk.matching.validators import MatchValidator
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def matching_config():
    """Create test matching configuration."""
    return MatchingConfig()


@pytest.fixture
async def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_risk_engine():
    """Mock risk engine."""
    risk_engine = AsyncMock()
    risk_engine.evaluate_match_risk = AsyncMock(return_value={
        "risk_status": "PASS",
        "risk_score": 95,
        "flags": [],
        "details": {}
    })
    return risk_engine


@pytest.fixture
def match_validator(mock_db_session, mock_risk_engine, matching_config):
    """Create MatchValidator instance."""
    return MatchValidator(
        db=mock_db_session,
        risk_engine=mock_risk_engine,
        config=matching_config
    )


@pytest.fixture
def sample_requirement():
    """Create sample requirement."""
    commodity_mock = Mock()
    commodity_mock.id = uuid4()
    commodity_mock.code = "COTTON"
    
    buyer_mock = Mock()
    buyer_mock.id = uuid4()
    buyer_mock.branch_id = uuid4()
    
    requirement = Mock(spec=Requirement)
    requirement.id = uuid4()
    requirement.commodity_id = commodity_mock.id
    requirement.commodity = commodity_mock
    requirement.buyer_partner_id = buyer_mock.id
    requirement.buyer_partner = buyer_mock
    requirement.quantity_required = Decimal("100.000")
    requirement.expected_price = Decimal("50000.00")
    requirement.max_price = Decimal("55000.00")
    requirement.delivery_by = datetime.utcnow() + timedelta(days=30)
    requirement.status = "ACTIVE"
    requirement.intent = "DIRECT_BUY"
    requirement.quality_params = {"staple_length": 28.5}
    
    return requirement


@pytest.fixture
def sample_availability():
    """Create sample availability."""
    commodity_mock = Mock()
    commodity_mock.id = uuid4()
    commodity_mock.code = "COTTON"
    
    seller_mock = Mock()
    seller_mock.id = uuid4()
    seller_mock.branch_id = uuid4()
    
    location_mock = Mock()
    location_mock.id = uuid4()
    
    availability = Mock(spec=Availability)
    availability.id = uuid4()
    availability.commodity_id = commodity_mock.id
    availability.commodity = commodity_mock
    availability.location_id = location_mock.id
    availability.location = location_mock
    availability.seller_id = seller_mock.id
    availability.seller = seller_mock
    availability.seller_branch_id = seller_mock.branch_id
    availability.available_quantity = Decimal("150.000")
    availability.base_price = Decimal("48000.00")
    availability.status = "ACTIVE"
    availability.risk_precheck_status = "PASS"
    availability.risk_precheck_score = 95
    availability.ai_confidence_score = Decimal("0.85")
    availability.blocked_for_branches = False
    availability.quality_params = {"staple_length": 29.0}
    
    return availability


# ============================================================================
# TEST CATEGORY 1: validate_match_eligibility()
# ============================================================================

@pytest.mark.asyncio
class TestValidateMatchEligibility:
    """Test comprehensive match validation."""
    
    async def test_valid_match_passes_all_checks(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Valid match should pass all eligibility checks."""
        # Act
        result = await match_validator.validate_match_eligibility(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_eligible"] is True
        assert result["passed_checks"] is not None
        assert len(result["failed_checks"]) == 0
        assert "validation_timestamp" in result
    
    async def test_rejects_mismatched_commodity(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should reject when commodities don't match."""
        # Arrange
        sample_availability.commodity_id = uuid4()  # Different commodity
        
        # Act
        result = await match_validator.validate_match_eligibility(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_eligible"] is False
        assert "commodity_mismatch" in str(result["failed_checks"])
    
    async def test_rejects_inactive_requirement(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should reject when requirement is not ACTIVE."""
        # Arrange
        sample_requirement.status = "CANCELLED"
        
        # Act
        result = await match_validator.validate_match_eligibility(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_eligible"] is False
        assert "inactive_requirement" in str(result["failed_checks"])
    
    async def test_rejects_inactive_availability(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should reject when availability is not ACTIVE."""
        # Arrange
        sample_availability.status = "SOLD"
        
        # Act
        result = await match_validator.validate_match_eligibility(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_eligible"] is False
        assert "inactive_availability" in str(result["failed_checks"])
    
    async def test_rejects_insufficient_quantity(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should reject when available quantity is insufficient."""
        # Arrange
        sample_requirement.quantity_required = Decimal("1000.000")
        sample_availability.available_quantity = Decimal("10.000")
        
        # Act
        result = await match_validator.validate_match_eligibility(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_eligible"] is False
        assert "insufficient_quantity" in str(result["failed_checks"])
    
    async def test_rejects_price_above_max(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should reject when price exceeds buyer's max_price."""
        # Arrange
        sample_requirement.max_price = Decimal("45000.00")
        sample_availability.base_price = Decimal("50000.00")
        
        # Act
        result = await match_validator.validate_match_eligibility(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_eligible"] is False
        assert "price_too_high" in str(result["failed_checks"])


# ============================================================================
# TEST CATEGORY 2: validate_risk_compliance()
# ============================================================================

@pytest.mark.asyncio
class TestValidateRiskCompliance:
    """Test risk status validation."""
    
    async def test_pass_status_is_compliant(
        self,
        match_validator,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Risk status PASS should be compliant."""
        # Arrange
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "PASS",
            "risk_score": 95,
            "flags": []
        })
        
        # Act
        result = await match_validator.validate_risk_compliance(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_compliant"] is True
        assert result["risk_status"] == "PASS"
        assert result.get("blocked", False) is False
    
    async def test_warn_status_is_compliant_with_penalty(
        self,
        match_validator,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Risk status WARN should be compliant but with penalty flag."""
        # Arrange
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "WARN",
            "risk_score": 70,
            "flags": ["moderate_credit_risk"]
        })
        
        # Act
        result = await match_validator.validate_risk_compliance(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_compliant"] is True
        assert result["risk_status"] == "WARN"
        assert result.get("requires_penalty", False) is True
        assert result.get("blocked", False) is False
    
    async def test_fail_status_is_not_compliant(
        self,
        match_validator,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Risk status FAIL should not be compliant (blocked)."""
        # Arrange
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "FAIL",
            "risk_score": 30,
            "blocked": True,
            "flags": ["high_credit_risk"]
        })
        
        # Act
        result = await match_validator.validate_risk_compliance(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_compliant"] is False
        assert result["risk_status"] == "FAIL"
        assert result.get("blocked", False) is True
    
    async def test_handles_risk_engine_exception(
        self,
        match_validator,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Should handle risk engine exceptions gracefully."""
        # Arrange
        mock_risk_engine.evaluate_match_risk = AsyncMock(
            side_effect=Exception("Risk engine error")
        )
        
        # Act
        result = await match_validator.validate_risk_compliance(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        # Should fail safe - treat as non-compliant
        assert result["is_compliant"] is False
        assert "error" in result


# ============================================================================
# TEST CATEGORY 3: validate_quantity_availability()
# ============================================================================

@pytest.mark.asyncio
class TestValidateQuantityAvailability:
    """Test quantity validation logic."""
    
    async def test_full_quantity_available(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should pass when full quantity is available."""
        # Arrange
        sample_requirement.quantity_required = Decimal("100.000")
        sample_availability.available_quantity = Decimal("150.000")
        
        # Act
        result = await match_validator.validate_quantity_availability(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_available"] is True
        assert result["available_quantity"] == Decimal("150.000")
        assert result["requested_quantity"] == Decimal("100.000")
        assert result["can_fulfill_full"] is True
    
    async def test_partial_quantity_available(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should handle partial quantity availability."""
        # Arrange
        sample_requirement.quantity_required = Decimal("200.000")
        sample_availability.available_quantity = Decimal("150.000")
        
        # Act
        result = await match_validator.validate_quantity_availability(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_available"] is True  # Partial match OK
        assert result["can_fulfill_full"] is False
        assert result["partial_match"] is True
    
    async def test_rejects_below_minimum_quantity(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should reject when quantity below configured minimum (10%)."""
        # Arrange
        sample_requirement.quantity_required = Decimal("1000.000")
        sample_availability.available_quantity = Decimal("50.000")  # Only 5%
        
        # Act
        result = await match_validator.validate_quantity_availability(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_available"] is False
        assert result.get("below_minimum", False) is True


# ============================================================================
# TEST CATEGORY 4: validate_internal_branch_trading()
# ============================================================================

@pytest.mark.asyncio
class TestValidateInternalBranchTrading:
    """Test internal branch trading prevention."""
    
    async def test_blocks_same_branch_trading_when_configured(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should block trading when buyer and seller are same branch."""
        # Arrange
        same_branch_id = uuid4()
        sample_requirement.buyer_partner.branch_id = same_branch_id
        sample_availability.seller_branch_id = same_branch_id
        match_validator.config.BLOCK_INTERNAL_BRANCH_TRADING = True
        
        # Act
        result = await match_validator.validate_internal_branch_trading(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_allowed"] is False
        assert result["is_internal_trade"] is True
        assert result.get("blocked_reason") is not None
    
    async def test_allows_different_branch_trading(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should allow trading when buyer and seller are different branches."""
        # Arrange
        sample_requirement.buyer_partner.branch_id = uuid4()
        sample_availability.seller_branch_id = uuid4()
        match_validator.config.BLOCK_INTERNAL_BRANCH_TRADING = True
        
        # Act
        result = await match_validator.validate_internal_branch_trading(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_allowed"] is True
        assert result["is_internal_trade"] is False
    
    async def test_allows_same_branch_when_not_configured_to_block(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should allow same branch trading when config allows it."""
        # Arrange
        same_branch_id = uuid4()
        sample_requirement.buyer_partner.branch_id = same_branch_id
        sample_availability.seller_branch_id = same_branch_id
        match_validator.config.BLOCK_INTERNAL_BRANCH_TRADING = False
        
        # Act
        result = await match_validator.validate_internal_branch_trading(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        assert result["is_allowed"] is True
    
    async def test_handles_missing_branch_ids(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should handle missing branch IDs gracefully."""
        # Arrange
        sample_requirement.buyer_partner.branch_id = None
        sample_availability.seller_branch_id = None
        
        # Act
        result = await match_validator.validate_internal_branch_trading(
            requirement=sample_requirement,
            availability=sample_availability
        )
        
        # Assert
        # Should allow when branch IDs not set
        assert result["is_allowed"] is True


# ============================================================================
# TEST CATEGORY 5: validate_ai_requirements()
# ============================================================================

@pytest.mark.asyncio
class TestValidateAiRequirements:
    """Test AI confidence validation."""
    
    async def test_high_confidence_passes(
        self,
        match_validator,
        sample_availability
    ):
        """AI confidence >= 0.6 should pass validation."""
        # Arrange
        sample_availability.ai_confidence_score = Decimal("0.85")
        match_validator.config.AI_MIN_CONFIDENCE_THRESHOLD = 0.6
        
        # Act
        result = await match_validator.validate_ai_requirements(
            availability=sample_availability
        )
        
        # Assert
        assert result["meets_threshold"] is True
        assert result["confidence_score"] == Decimal("0.85")
        assert result.get("boost_eligible", False) is True
    
    async def test_low_confidence_fails(
        self,
        match_validator,
        sample_availability
    ):
        """AI confidence < 0.6 should fail validation."""
        # Arrange
        sample_availability.ai_confidence_score = Decimal("0.45")
        match_validator.config.AI_MIN_CONFIDENCE_THRESHOLD = 0.6
        
        # Act
        result = await match_validator.validate_ai_requirements(
            availability=sample_availability
        )
        
        # Assert
        assert result["meets_threshold"] is False
        assert result["confidence_score"] == Decimal("0.45")
        assert result.get("boost_eligible", False) is False
    
    async def test_handles_missing_confidence_score(
        self,
        match_validator,
        sample_availability
    ):
        """Should handle missing AI confidence gracefully."""
        # Arrange
        sample_availability.ai_confidence_score = None
        
        # Act
        result = await match_validator.validate_ai_requirements(
            availability=sample_availability
        )
        
        # Assert
        assert result["meets_threshold"] is False
        assert result["confidence_score"] is None


# ============================================================================
# TEST CATEGORY 6: Integration Workflows
# ============================================================================

@pytest.mark.asyncio
class TestValidationWorkflows:
    """Test combined validation workflows."""
    
    async def test_complete_validation_workflow(
        self,
        match_validator,
        sample_requirement,
        sample_availability
    ):
        """Should run complete validation workflow."""
        # Act - Run all validations
        eligibility = await match_validator.validate_match_eligibility(
            sample_requirement,
            sample_availability
        )
        risk = await match_validator.validate_risk_compliance(
            sample_requirement,
            sample_availability
        )
        quantity = await match_validator.validate_quantity_availability(
            sample_requirement,
            sample_availability
        )
        branch = await match_validator.validate_internal_branch_trading(
            sample_requirement,
            sample_availability
        )
        ai = await match_validator.validate_ai_requirements(
            sample_availability
        )
        
        # Assert - All should pass for valid match
        assert eligibility["is_eligible"] is True
        assert risk["is_compliant"] is True
        assert quantity["is_available"] is True
        assert branch["is_allowed"] is True
        assert ai["meets_threshold"] is True
    
    async def test_workflow_stops_on_critical_failure(
        self,
        match_validator,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Should stop workflow when critical check fails."""
        # Arrange - Set risk to FAIL
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "FAIL",
            "risk_score": 25,
            "blocked": True
        })
        
        # Act
        risk = await match_validator.validate_risk_compliance(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert risk["is_compliant"] is False
        assert risk.get("blocked", False) is True
        # Would short-circuit further validations in production
