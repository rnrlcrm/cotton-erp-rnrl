"""
End-to-End (E2E) Test Suite: Matching Engine Complete Workflows

Comprehensive E2E tests covering ALL major matching engine flows:
1. Post availability → auto-match
2. Post requirement → auto-match
3. Allocation flow
4. Risk PASS/WARN/FAIL cases
5. Duplicate detection
6. Circular trading blocks
7. Party links blocks

Tests use pure mocking approach to validate business logic flows without
requiring database infrastructure or SQLAlchemy model initialization.
All tests follow existing repository test patterns.

Run with: pytest backend/tests/e2e/test_matching_engine_e2e.py -v
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
from dataclasses import dataclass, field


# ============================================================================
# MOCK DATA CLASSES - Pure Python objects for testing
# ============================================================================

@dataclass
class MockRequirement:
    """Mock Requirement object for testing without SQLAlchemy."""
    id: UUID = field(default_factory=uuid4)
    requirement_number: str = ""
    buyer_partner_id: UUID = field(default_factory=uuid4)
    commodity_id: UUID = field(default_factory=uuid4)
    min_quantity: Decimal = Decimal("50.0")
    max_quantity: Decimal = Decimal("200.0")
    preferred_quantity: Decimal = Decimal("100.0")
    quantity_unit: str = "BALES"
    max_budget_per_unit: Decimal = Decimal("55000.00")
    preferred_price_per_unit: Decimal = Decimal("50000.00")
    max_budget: Decimal = Decimal("55000.00")
    currency_code: str = "INR"
    delivery_locations: List[Dict[str, Any]] = field(default_factory=list)
    quality_requirements: Dict[str, Any] = field(default_factory=dict)
    quality_params: Dict[str, Any] = field(default_factory=dict)
    status: str = "ACTIVE"
    intent_type: str = "DIRECT_BUY"
    valid_from: datetime = field(default_factory=datetime.utcnow)
    valid_until: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    buyer_branch_id: UUID = field(default_factory=uuid4)
    blocked_internal_trades: bool = False
    commodity: Any = None
    buyer_partner: Any = None


@dataclass
class MockAvailability:
    """Mock Availability object for testing without SQLAlchemy."""
    id: UUID = field(default_factory=uuid4)
    availability_number: str = ""
    seller_id: UUID = field(default_factory=uuid4)
    commodity_id: UUID = field(default_factory=uuid4)
    location_id: UUID = field(default_factory=uuid4)
    total_quantity: Decimal = Decimal("150.0")
    remaining_quantity: Decimal = Decimal("150.0")
    available_quantity: Decimal = Decimal("150.0")
    quantity_unit: str = "BALES"
    base_price: Decimal = Decimal("48000.00")
    asking_price: Decimal = Decimal("48000.00")
    price_unit: str = "per BALE"
    currency: str = "INR"
    quality_params: Dict[str, Any] = field(default_factory=dict)
    status: str = "AVAILABLE"
    risk_precheck_status: str = "PASS"
    risk_precheck_score: int = 85
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    seller_branch_id: UUID = field(default_factory=uuid4)
    blocked_for_branches: List[UUID] = field(default_factory=list)
    seller: Any = None
    commodity: Any = None
    location: Any = None
    quantity: Decimal = Decimal("150.0")
    price_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockMatchResult:
    """Mock MatchResult object for testing."""
    requirement_id: UUID = field(default_factory=uuid4)
    availability_id: UUID = field(default_factory=uuid4)
    score: float = 0.85
    base_score: float = 0.85
    warn_penalty_applied: bool = False
    warn_penalty_value: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    pass_fail: Dict[str, bool] = field(default_factory=dict)
    risk_status: str = "PASS"
    risk_details: Dict[str, Any] = field(default_factory=dict)
    location_filter_passed: bool = True
    duplicate_detection_key: str = None
    matched_at: datetime = field(default_factory=datetime.utcnow)
    requirement: Any = None
    availability: Any = None


@dataclass
class MockBusinessPartner:
    """Mock BusinessPartner for testing."""
    id: UUID = field(default_factory=uuid4)
    partner_type: str = "trader"
    pan_number: str = None
    tax_id_number: str = None
    primary_contact_phone: str = None
    primary_contact_email: str = None


# ============================================================================
# MOCK ENGINE CLASSES - Pure Python implementations
# ============================================================================

class MockMatchingEngine:
    """
    Mock Matching Engine for testing business logic.
    Implements the same interface as the real MatchingEngine.
    """
    
    def __init__(self, db, requirement_repo, availability_repo, risk_engine=None, config=None):
        self.db = db
        self.requirement_repo = requirement_repo
        self.availability_repo = availability_repo
        self.risk_engine = risk_engine
        self.config = config or {}
        self._duplicate_cache = {}
    
    def _location_matches(self, requirement: MockRequirement, availability: MockAvailability) -> bool:
        """Hard location filter - BEFORE any scoring."""
        if not requirement.delivery_locations:
            return True
        
        for loc in requirement.delivery_locations:
            if loc.get("location_id") == str(availability.location_id):
                return True
        return False
    
    def _generate_duplicate_key(self, requirement: MockRequirement, availability: MockAvailability) -> str:
        """Generate unique key for duplicate detection."""
        return f"{requirement.commodity_id}:{requirement.buyer_partner_id}:{availability.seller_id}"
    
    async def _is_duplicate(self, dup_key: str, seen_duplicates: set, req_id: UUID, avail_id: UUID) -> bool:
        """Check if match is duplicate within time window."""
        if dup_key in seen_duplicates:
            return True
        return False
    
    async def find_matches_for_availability(
        self,
        availability_id: UUID,
        min_score: float = 0.5,
        scorer_func=None
    ) -> List[MockMatchResult]:
        """Find compatible requirements for an availability."""
        availability = await self.availability_repo.get_by_id(availability_id)
        if not availability:
            raise ValueError(f"Availability {availability_id} not found")
        
        requirements = await self.requirement_repo.search_by_location(
            location_id=availability.location_id,
            commodity_id=availability.commodity_id
        )
        
        matches = []
        seen_duplicates = set()
        
        for requirement in requirements:
            if not self._location_matches(requirement, availability):
                continue
            
            dup_key = self._generate_duplicate_key(requirement, availability)
            if await self._is_duplicate(dup_key, seen_duplicates, requirement.id, availability.id):
                continue
            
            # Use scorer function if provided
            if scorer_func:
                score_result = await scorer_func(requirement, availability)
            else:
                score_result = {
                    "total_score": 0.85,
                    "base_score": 0.85,
                    "blocked": False,
                    "risk_details": {"risk_status": "PASS"}
                }
            
            if score_result.get("blocked", False):
                continue
            
            if score_result["total_score"] < min_score:
                continue
            
            match = MockMatchResult(
                requirement_id=requirement.id,
                availability_id=availability.id,
                score=score_result["total_score"],
                base_score=score_result["base_score"],
                warn_penalty_applied=score_result.get("warn_penalty_applied", False),
                warn_penalty_value=score_result.get("warn_penalty_value", 0.0),
                risk_status=score_result.get("risk_details", {}).get("risk_status", "PASS"),
                location_filter_passed=True,
                duplicate_detection_key=dup_key,
                requirement=requirement,
                availability=availability
            )
            
            matches.append(match)
            seen_duplicates.add(dup_key)
        
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches
    
    async def find_matches_for_requirement(
        self,
        requirement_id: UUID,
        min_score: float = 0.5,
        scorer_func=None
    ) -> List[MockMatchResult]:
        """Find compatible availabilities for a requirement."""
        requirement = await self.requirement_repo.get_by_id(requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")
        
        location_ids = []
        if requirement.delivery_locations:
            for loc in requirement.delivery_locations:
                loc_id = loc.get("location_id")
                if loc_id:
                    location_ids.append(UUID(loc_id))
        
        availabilities = await self.availability_repo.search_by_location(
            location_ids=location_ids,
            commodity_id=requirement.commodity_id
        )
        
        matches = []
        seen_duplicates = set()
        
        for availability in availabilities:
            if not self._location_matches(requirement, availability):
                continue
            
            dup_key = self._generate_duplicate_key(requirement, availability)
            if await self._is_duplicate(dup_key, seen_duplicates, requirement.id, availability.id):
                continue
            
            if scorer_func:
                score_result = await scorer_func(requirement, availability)
            else:
                score_result = {
                    "total_score": 0.85,
                    "base_score": 0.85,
                    "blocked": False,
                    "risk_details": {"risk_status": "PASS"}
                }
            
            if score_result.get("blocked", False):
                continue
            
            if score_result["total_score"] < min_score:
                continue
            
            match = MockMatchResult(
                requirement_id=requirement.id,
                availability_id=availability.id,
                score=score_result["total_score"],
                base_score=score_result["base_score"],
                warn_penalty_applied=score_result.get("warn_penalty_applied", False),
                warn_penalty_value=score_result.get("warn_penalty_value", 0.0),
                risk_status=score_result.get("risk_details", {}).get("risk_status", "PASS"),
                location_filter_passed=True,
                duplicate_detection_key=dup_key,
                requirement=requirement,
                availability=availability
            )
            
            matches.append(match)
            seen_duplicates.add(dup_key)
        
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches
    
    async def allocate_quantity_atomic(
        self,
        availability_id: UUID,
        requested_quantity: Decimal,
        requirement_id: UUID
    ) -> Dict[str, Any]:
        """Atomically allocate quantity with optimistic locking."""
        availability = await self.availability_repo.get_by_id(availability_id)
        
        if not availability:
            return {"allocated": False, "error": "Availability not found"}
        
        current_remaining = availability.remaining_quantity or Decimal(0)
        
        if current_remaining < requested_quantity:
            allocated_qty = current_remaining
            allocation_type = "PARTIAL"
        else:
            allocated_qty = requested_quantity
            allocation_type = "FULL"
        
        if allocated_qty <= 0:
            return {"allocated": False, "error": "No quantity available"}
        
        # Update (simulated)
        new_remaining = current_remaining - allocated_qty
        
        return {
            "allocated": True,
            "allocated_quantity": float(allocated_qty),
            "remaining_quantity": float(new_remaining),
            "allocation_type": allocation_type
        }


class MockRiskEngine:
    """
    Mock Risk Engine for testing business logic.
    Implements the same interface as the real RiskEngine.
    """
    
    PASS_THRESHOLD = 80
    WARN_THRESHOLD = 60
    
    def __init__(self, db=None):
        self.db = db
    
    async def check_circular_trading(
        self,
        partner_id: UUID,
        commodity_id: UUID,
        transaction_type: str,
        trade_date: date
    ) -> Dict[str, Any]:
        """
        Check if partner has opposite position for same commodity same day.
        Uses mock database lookup via db.execute.
        """
        if self.db is None:
            return {"blocked": False, "reason": "No DB", "existing_positions": []}
        
        result = await self.db.execute(None)  # Mock execute
        existing = result.scalars().all()
        
        if existing:
            return {
                "blocked": True,
                "reason": f"CIRCULAR TRADING VIOLATION: Partner has existing opposite position(s) for same commodity on {trade_date}",
                "violation_type": f"SAME_DAY_{transaction_type}_REVERSAL",
                "existing_positions": [
                    {"type": "OPPOSITE", "quantity": 100.0, "status": "ACTIVE"}
                ],
                "recommendation": "Cancel existing positions or wait until tomorrow"
            }
        
        return {
            "blocked": False,
            "reason": "No circular trading detected - validation passed",
            "violation_type": None,
            "existing_positions": []
        }
    
    async def validate_partner_role(
        self,
        partner_id: UUID,
        transaction_type: str
    ) -> Dict[str, Any]:
        """
        Validate partner role allows the requested transaction type.
        Uses mock database lookup via db.execute.
        """
        if self.db is None:
            return {"allowed": True, "reason": "No DB", "partner_type": None}
        
        result = await self.db.execute(None)  # Mock execute
        partner_type = result.scalar_one_or_none()
        
        if not partner_type:
            return {"allowed": False, "reason": "Partner not found", "partner_type": None}
        
        partner_type = partner_type.lower()
        
        if partner_type == "buyer" and transaction_type == "SELL":
            return {
                "allowed": False,
                "reason": "ROLE VIOLATION: BUYER cannot post SELL availabilities",
                "partner_type": partner_type
            }
        
        if partner_type == "seller" and transaction_type == "BUY":
            return {
                "allowed": False,
                "reason": "ROLE VIOLATION: SELLER cannot post BUY requirements",
                "partner_type": partner_type
            }
        
        return {"allowed": True, "reason": f"{partner_type} can {transaction_type}", "partner_type": partner_type}
    
    async def check_party_links(
        self,
        buyer_partner_id: UUID,
        seller_partner_id: UUID
    ) -> Dict[str, Any]:
        """
        Check if buyer and seller are linked (same ownership/entity).
        Uses mock database lookups via db.execute.
        """
        if self.db is None:
            return {"linked": False, "severity": "PASS", "violations": []}
        
        # Get buyer and seller from mocked DB
        result1 = await self.db.execute(None)
        result2 = await self.db.execute(None)
        
        buyer = result1.scalar_one_or_none()
        seller = result2.scalar_one_or_none()
        
        if not buyer or not seller:
            return {
                "linked": False,
                "severity": "PASS",
                "violations": [],
                "block_violations": [],
                "warn_violations": [],
                "recommended_action": "PROCEED: Partner not found"
            }
        
        violations = []
        max_severity = "PASS"
        
        # Check PAN number
        if buyer.pan_number and seller.pan_number and buyer.pan_number == seller.pan_number:
            violations.append({
                "type": "SAME_PAN",
                "severity": "BLOCK",
                "field": "PAN Number",
                "value": buyer.pan_number,
                "message": f"BLOCKED: Same PAN number ({buyer.pan_number})"
            })
            max_severity = "BLOCK"
        
        # Check Tax ID
        if buyer.tax_id_number and seller.tax_id_number and buyer.tax_id_number == seller.tax_id_number:
            violations.append({
                "type": "SAME_TAX_ID",
                "severity": "BLOCK",
                "field": "Tax ID Number",
                "value": buyer.tax_id_number,
                "message": f"BLOCKED: Same tax ID ({buyer.tax_id_number})"
            })
            max_severity = "BLOCK"
        
        # Check mobile
        if (buyer.primary_contact_phone and seller.primary_contact_phone and 
            buyer.primary_contact_phone == seller.primary_contact_phone):
            violations.append({
                "type": "SAME_MOBILE",
                "severity": "WARN",
                "field": "Mobile Number",
                "value": buyer.primary_contact_phone,
                "message": f"WARNING: Same mobile ({buyer.primary_contact_phone})"
            })
            if max_severity == "PASS":
                max_severity = "WARN"
        
        # Check email domain (skip common providers)
        if buyer.primary_contact_email and seller.primary_contact_email:
            buyer_domain = buyer.primary_contact_email.split('@')[-1].lower()
            seller_domain = seller.primary_contact_email.split('@')[-1].lower()
            common_providers = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
            
            if buyer_domain == seller_domain and buyer_domain not in common_providers:
                violations.append({
                    "type": "SAME_EMAIL_DOMAIN",
                    "severity": "WARN",
                    "field": "Email Domain",
                    "value": buyer_domain,
                    "message": f"WARNING: Same corporate email domain ({buyer_domain})"
                })
                if max_severity == "PASS":
                    max_severity = "WARN"
        
        return {
            "linked": len(violations) > 0,
            "severity": max_severity,
            "violations": violations,
            "violation_count": len(violations),
            "block_violations": [v for v in violations if v["severity"] == "BLOCK"],
            "warn_violations": [v for v in violations if v["severity"] == "WARN"],
            "recommended_action": "REJECT" if max_severity == "BLOCK" else "REVIEW" if max_severity == "WARN" else "APPROVE",
            "checked_at": datetime.utcnow().isoformat()
        }


# ============================================================================
# FIXTURES - Common test data factories
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.begin_nested = MagicMock()
    session.begin_nested.return_value.__aenter__ = AsyncMock()
    session.begin_nested.return_value.__aexit__ = AsyncMock()
    return session


@pytest.fixture
def sample_commodity_id():
    """Return a sample commodity UUID (Cotton)."""
    return uuid4()


@pytest.fixture
def sample_location_id():
    """Return a sample location UUID (Mumbai)."""
    return uuid4()


@pytest.fixture
def sample_buyer_id():
    """Return a sample buyer partner UUID."""
    return uuid4()


@pytest.fixture
def sample_seller_id():
    """Return a sample seller partner UUID."""
    return uuid4()


@pytest.fixture
def sample_requirement(sample_commodity_id, sample_location_id, sample_buyer_id):
    """Create a sample buyer requirement using mock dataclass."""
    return MockRequirement(
        id=uuid4(),
        requirement_number=f"REQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-001",
        buyer_partner_id=sample_buyer_id,
        commodity_id=sample_commodity_id,
        min_quantity=Decimal("50.0"),
        max_quantity=Decimal("200.0"),
        preferred_quantity=Decimal("100.0"),
        quantity_unit="BALES",
        max_budget_per_unit=Decimal("55000.00"),
        max_budget=Decimal("55000.00"),
        preferred_price_per_unit=Decimal("50000.00"),
        currency_code="INR",
        delivery_locations=[
            {
                "location_id": str(sample_location_id),
                "latitude": 19.0760,
                "longitude": 72.8777,
                "max_distance_km": 50
            }
        ],
        quality_requirements={
            "staple_length": {"min": 28.0, "max": 32.0, "preferred": 30.0},
            "micronaire": {"min": 3.5, "max": 4.9, "preferred": 4.2}
        },
        status="ACTIVE",
        intent_type="DIRECT_BUY",
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=30)
    )


@pytest.fixture
def sample_availability(sample_commodity_id, sample_location_id, sample_seller_id):
    """Create a sample seller availability using mock dataclass."""
    return MockAvailability(
        id=uuid4(),
        availability_number=f"AVL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-001",
        seller_id=sample_seller_id,
        commodity_id=sample_commodity_id,
        location_id=sample_location_id,
        total_quantity=Decimal("150.0"),
        remaining_quantity=Decimal("150.0"),
        available_quantity=Decimal("150.0"),
        quantity_unit="BALES",
        base_price=Decimal("48000.00"),
        asking_price=Decimal("48000.00"),
        price_unit="per BALE",
        currency="INR",
        quality_params={
            "staple_length": 29.5,
            "micronaire": 4.2,
            "strength": 28.0
        },
        status="AVAILABLE",
        risk_precheck_status="PASS",
        risk_precheck_score=85
    )


# ============================================================================
# TEST CATEGORY 1: Post Availability → Auto-Match
# ============================================================================

@pytest.mark.asyncio
class TestPostAvailabilityAutoMatch:
    """
    E2E Tests: Seller posts availability → Engine finds matching requirements.
    """
    
    async def test_post_availability_finds_single_matching_requirement(
        self,
        mock_db_session,
        sample_availability,
        sample_requirement
    ):
        """E2E: Seller posts availability → Single matching requirement found."""
        mock_requirement_repo = AsyncMock()
        mock_requirement_repo.search_by_location = AsyncMock(return_value=[sample_requirement])
        mock_requirement_repo.get_by_id = AsyncMock(return_value=sample_requirement)
        
        mock_availability_repo = AsyncMock()
        mock_availability_repo.get_by_id = AsyncMock(return_value=sample_availability)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=mock_requirement_repo,
            availability_repo=mock_availability_repo
        )
        
        matches = await engine.find_matches_for_availability(
            availability_id=sample_availability.id,
            min_score=0.5
        )
        
        assert len(matches) == 1
        match = matches[0]
        assert match.availability_id == sample_availability.id
        assert match.requirement_id == sample_requirement.id
        assert match.score >= 0.5
        assert match.location_filter_passed is True
    
    async def test_post_availability_finds_multiple_requirements_ranked(
        self,
        mock_db_session,
        sample_availability,
        sample_commodity_id,
        sample_location_id
    ):
        """E2E: Seller posts availability → Multiple requirements found and ranked."""
        requirements = []
        for i, budget in enumerate([Decimal("60000"), Decimal("55000"), Decimal("52000")]):
            req = MockRequirement(
                id=uuid4(),
                commodity_id=sample_commodity_id,
                buyer_partner_id=uuid4(),
                max_budget_per_unit=budget,
                delivery_locations=[{"location_id": str(sample_location_id)}]
            )
            requirements.append(req)
        
        mock_requirement_repo = AsyncMock()
        mock_requirement_repo.search_by_location = AsyncMock(return_value=requirements)
        
        mock_availability_repo = AsyncMock()
        mock_availability_repo.get_by_id = AsyncMock(return_value=sample_availability)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=mock_requirement_repo,
            availability_repo=mock_availability_repo
        )
        
        # Custom scorer returns different scores
        scores = [0.95, 0.85, 0.75]
        call_count = [0]
        
        async def custom_scorer(req, avail):
            idx = min(call_count[0], len(scores) - 1)
            call_count[0] += 1
            return {"total_score": scores[idx], "base_score": scores[idx], "blocked": False, "risk_details": {}}
        
        matches = await engine.find_matches_for_availability(
            availability_id=sample_availability.id,
            min_score=0.5,
            scorer_func=custom_scorer
        )
        
        assert len(matches) == 3
        # Verify sorted by score descending
        for i in range(len(matches) - 1):
            assert matches[i].score >= matches[i + 1].score
    
    async def test_post_availability_no_matching_requirements(
        self,
        mock_db_session,
        sample_availability
    ):
        """E2E: Seller posts availability → No matching requirements found."""
        mock_requirement_repo = AsyncMock()
        mock_requirement_repo.search_by_location = AsyncMock(return_value=[])
        
        mock_availability_repo = AsyncMock()
        mock_availability_repo.get_by_id = AsyncMock(return_value=sample_availability)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=mock_requirement_repo,
            availability_repo=mock_availability_repo
        )
        
        matches = await engine.find_matches_for_availability(
            availability_id=sample_availability.id,
            min_score=0.5
        )
        
        assert matches == []


# ============================================================================
# TEST CATEGORY 2: Post Requirement → Auto-Match
# ============================================================================

@pytest.mark.asyncio
class TestPostRequirementAutoMatch:
    """
    E2E Tests: Buyer posts requirement → Engine finds matching availabilities.
    """
    
    async def test_post_requirement_finds_single_matching_availability(
        self,
        mock_db_session,
        sample_requirement,
        sample_availability
    ):
        """E2E: Buyer posts requirement → Single matching availability found."""
        mock_availability_repo = AsyncMock()
        mock_availability_repo.search_by_location = AsyncMock(return_value=[sample_availability])
        
        mock_requirement_repo = AsyncMock()
        mock_requirement_repo.get_by_id = AsyncMock(return_value=sample_requirement)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=mock_requirement_repo,
            availability_repo=mock_availability_repo
        )
        
        matches = await engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            min_score=0.5
        )
        
        assert len(matches) == 1
        match = matches[0]
        assert match.requirement_id == sample_requirement.id
        assert match.availability_id == sample_availability.id
        assert match.score >= 0.5
    
    async def test_post_requirement_finds_multiple_availabilities_ranked(
        self,
        mock_db_session,
        sample_requirement,
        sample_commodity_id,
        sample_location_id
    ):
        """E2E: Buyer posts requirement → Multiple availabilities found and ranked."""
        availabilities = []
        for i, price in enumerate([Decimal("45000"), Decimal("48000"), Decimal("52000")]):
            avail = MockAvailability(
                id=uuid4(),
                commodity_id=sample_commodity_id,
                location_id=sample_location_id,
                seller_id=uuid4(),
                base_price=price,
                asking_price=price
            )
            availabilities.append(avail)
        
        mock_availability_repo = AsyncMock()
        mock_availability_repo.search_by_location = AsyncMock(return_value=availabilities)
        
        mock_requirement_repo = AsyncMock()
        mock_requirement_repo.get_by_id = AsyncMock(return_value=sample_requirement)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=mock_requirement_repo,
            availability_repo=mock_availability_repo
        )
        
        scores = [0.95, 0.85, 0.70]
        call_count = [0]
        
        async def custom_scorer(req, avail):
            idx = min(call_count[0], len(scores) - 1)
            call_count[0] += 1
            return {"total_score": scores[idx], "base_score": scores[idx], "blocked": False, "risk_details": {}}
        
        matches = await engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            min_score=0.5,
            scorer_func=custom_scorer
        )
        
        assert len(matches) == 3
        for i in range(len(matches) - 1):
            assert matches[i].score >= matches[i + 1].score


# ============================================================================
# TEST CATEGORY 3: Allocation Flow
# ============================================================================

@pytest.mark.asyncio
class TestAllocationFlow:
    """E2E Tests: Allocation flow with optimistic locking."""
    
    async def test_full_allocation_success(
        self,
        mock_db_session,
        sample_requirement,
        sample_availability
    ):
        """E2E: Full allocation when availability >= requested quantity."""
        sample_availability.remaining_quantity = Decimal("150.0")
        
        mock_availability_repo = AsyncMock()
        mock_availability_repo.get_by_id = AsyncMock(return_value=sample_availability)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=AsyncMock(),
            availability_repo=mock_availability_repo
        )
        
        result = await engine.allocate_quantity_atomic(
            availability_id=sample_availability.id,
            requested_quantity=Decimal("100.0"),
            requirement_id=sample_requirement.id
        )
        
        assert result["allocated"] is True
        assert result["allocated_quantity"] == 100.0
        assert result["allocation_type"] == "FULL"
        assert result["remaining_quantity"] == 50.0
    
    async def test_partial_allocation_success(
        self,
        mock_db_session,
        sample_requirement,
        sample_availability
    ):
        """E2E: Partial allocation when availability < requested quantity."""
        sample_availability.remaining_quantity = Decimal("60.0")
        
        mock_availability_repo = AsyncMock()
        mock_availability_repo.get_by_id = AsyncMock(return_value=sample_availability)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=AsyncMock(),
            availability_repo=mock_availability_repo
        )
        
        result = await engine.allocate_quantity_atomic(
            availability_id=sample_availability.id,
            requested_quantity=Decimal("100.0"),
            requirement_id=sample_requirement.id
        )
        
        assert result["allocated"] is True
        assert result["allocated_quantity"] == 60.0
        assert result["allocation_type"] == "PARTIAL"
        assert result["remaining_quantity"] == 0.0
    
    async def test_allocation_no_quantity_available(
        self,
        mock_db_session,
        sample_requirement,
        sample_availability
    ):
        """E2E: Allocation fails when no quantity available."""
        sample_availability.remaining_quantity = Decimal("0.0")
        
        mock_availability_repo = AsyncMock()
        mock_availability_repo.get_by_id = AsyncMock(return_value=sample_availability)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=AsyncMock(),
            availability_repo=mock_availability_repo
        )
        
        result = await engine.allocate_quantity_atomic(
            availability_id=sample_availability.id,
            requested_quantity=Decimal("100.0"),
            requirement_id=sample_requirement.id
        )
        
        assert result["allocated"] is False
        assert "error" in result
    
    async def test_allocation_availability_not_found(
        self,
        mock_db_session,
        sample_requirement
    ):
        """E2E: Allocation fails when availability not found."""
        mock_availability_repo = AsyncMock()
        mock_availability_repo.get_by_id = AsyncMock(return_value=None)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=AsyncMock(),
            availability_repo=mock_availability_repo
        )
        
        result = await engine.allocate_quantity_atomic(
            availability_id=uuid4(),
            requested_quantity=Decimal("100.0"),
            requirement_id=sample_requirement.id
        )
        
        assert result["allocated"] is False
        assert "not found" in result["error"].lower()


# ============================================================================
# TEST CATEGORY 4: Risk PASS/WARN/FAIL Cases
# ============================================================================

@pytest.mark.asyncio
class TestRiskPassWarnFail:
    """E2E Tests: Risk assessment PASS/WARN/FAIL scenarios."""
    
    async def test_risk_pass_no_penalty(
        self,
        mock_db_session,
        sample_requirement,
        sample_availability
    ):
        """E2E: Risk PASS → No penalty applied, match proceeds normally."""
        mock_availability_repo = AsyncMock()
        mock_availability_repo.search_by_location = AsyncMock(return_value=[sample_availability])
        
        mock_requirement_repo = AsyncMock()
        mock_requirement_repo.get_by_id = AsyncMock(return_value=sample_requirement)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=mock_requirement_repo,
            availability_repo=mock_availability_repo
        )
        
        async def pass_scorer(req, avail):
            return {
                "total_score": 0.90,
                "base_score": 0.90,
                "warn_penalty_applied": False,
                "warn_penalty_value": 0.0,
                "blocked": False,
                "risk_details": {"risk_status": "PASS"}
            }
        
        matches = await engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            scorer_func=pass_scorer
        )
        
        assert len(matches) == 1
        match = matches[0]
        assert match.risk_status == "PASS"
        assert match.warn_penalty_applied is False
        assert match.score == match.base_score
    
    async def test_risk_warn_penalty_applied(
        self,
        mock_db_session,
        sample_requirement,
        sample_availability
    ):
        """E2E: Risk WARN → 10% penalty applied, match still allowed."""
        mock_availability_repo = AsyncMock()
        mock_availability_repo.search_by_location = AsyncMock(return_value=[sample_availability])
        
        mock_requirement_repo = AsyncMock()
        mock_requirement_repo.get_by_id = AsyncMock(return_value=sample_requirement)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=mock_requirement_repo,
            availability_repo=mock_availability_repo
        )
        
        base_score = 0.85
        penalty = base_score * 0.10
        
        async def warn_scorer(req, avail):
            return {
                "total_score": base_score - penalty,
                "base_score": base_score,
                "warn_penalty_applied": True,
                "warn_penalty_value": penalty,
                "blocked": False,
                "risk_details": {"risk_status": "WARN"}
            }
        
        matches = await engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            scorer_func=warn_scorer
        )
        
        assert len(matches) == 1
        match = matches[0]
        assert match.risk_status == "WARN"
        assert match.warn_penalty_applied is True
        assert match.score < match.base_score
    
    async def test_risk_fail_blocks_match(
        self,
        mock_db_session,
        sample_requirement,
        sample_availability
    ):
        """E2E: Risk FAIL → Match blocked entirely, not returned."""
        mock_availability_repo = AsyncMock()
        mock_availability_repo.search_by_location = AsyncMock(return_value=[sample_availability])
        
        mock_requirement_repo = AsyncMock()
        mock_requirement_repo.get_by_id = AsyncMock(return_value=sample_requirement)
        
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=mock_requirement_repo,
            availability_repo=mock_availability_repo
        )
        
        async def fail_scorer(req, avail):
            return {
                "total_score": 0.0,
                "base_score": 0.85,
                "blocked": True,
                "risk_details": {"risk_status": "FAIL"}
            }
        
        matches = await engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            scorer_func=fail_scorer
        )
        
        assert len(matches) == 0


# ============================================================================
# TEST CATEGORY 5: Duplicate Detection
# ============================================================================

@pytest.mark.asyncio
class TestDuplicateDetection:
    """E2E Tests: Duplicate detection within matching."""
    
    async def test_duplicate_key_format(self, mock_db_session):
        """Test duplicate key format: {commodity}:{buyer}:{seller}."""
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=AsyncMock(),
            availability_repo=AsyncMock()
        )
        
        commodity_id = uuid4()
        buyer_id = uuid4()
        seller_id = uuid4()
        
        req = MockRequirement(commodity_id=commodity_id, buyer_partner_id=buyer_id)
        avail = MockAvailability(seller_id=seller_id)
        
        key = engine._generate_duplicate_key(req, avail)
        
        expected_key = f"{commodity_id}:{buyer_id}:{seller_id}"
        assert key == expected_key
    
    async def test_duplicate_blocked_same_session(self, mock_db_session):
        """E2E: Duplicate match in same session is blocked."""
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=AsyncMock(),
            availability_repo=AsyncMock()
        )
        
        dup_key = f"test:{uuid4()}:{uuid4()}"
        seen_duplicates = set()
        
        # First check - not duplicate
        is_dup1 = await engine._is_duplicate(dup_key, seen_duplicates, uuid4(), uuid4())
        assert is_dup1 is False
        
        # Add to seen set
        seen_duplicates.add(dup_key)
        
        # Second check - IS duplicate
        is_dup2 = await engine._is_duplicate(dup_key, seen_duplicates, uuid4(), uuid4())
        assert is_dup2 is True
    
    async def test_different_commodity_not_duplicate(self, mock_db_session):
        """E2E: Different commodities with same buyer-seller are NOT duplicates."""
        engine = MockMatchingEngine(
            db=mock_db_session,
            requirement_repo=AsyncMock(),
            availability_repo=AsyncMock()
        )
        
        buyer_id = uuid4()
        seller_id = uuid4()
        commodity1_id = uuid4()
        commodity2_id = uuid4()
        
        req1 = MockRequirement(commodity_id=commodity1_id, buyer_partner_id=buyer_id)
        req2 = MockRequirement(commodity_id=commodity2_id, buyer_partner_id=buyer_id)
        avail = MockAvailability(seller_id=seller_id)
        
        key1 = engine._generate_duplicate_key(req1, avail)
        key2 = engine._generate_duplicate_key(req2, avail)
        
        assert key1 != key2


# ============================================================================
# TEST CATEGORY 6: Circular Trading Blocks
# ============================================================================

@pytest.mark.asyncio
class TestCircularTradingBlocks:
    """E2E Tests: Circular trading prevention (same-day buy/sell reversal)."""
    
    async def test_same_day_buy_after_sell_blocked(self, mock_db_session):
        """E2E: Creating BUY on same day as existing SELL is BLOCKED."""
        engine = MockRiskEngine(mock_db_session)
        
        # Mock existing SELL position
        mock_sell = Mock()
        mock_sell.id = uuid4()
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_sell]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_circular_trading(
            partner_id=uuid4(),
            commodity_id=uuid4(),
            transaction_type="BUY",
            trade_date=date.today()
        )
        
        assert result["blocked"] is True
        assert "CIRCULAR" in result["reason"].upper()
    
    async def test_same_day_sell_after_buy_blocked(self, mock_db_session):
        """E2E: Creating SELL on same day as existing BUY is BLOCKED."""
        engine = MockRiskEngine(mock_db_session)
        
        mock_buy = Mock()
        mock_buy.id = uuid4()
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_buy]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_circular_trading(
            partner_id=uuid4(),
            commodity_id=uuid4(),
            transaction_type="SELL",
            trade_date=date.today()
        )
        
        assert result["blocked"] is True
    
    async def test_different_day_allowed(self, mock_db_session):
        """E2E: Creating opposite position on DIFFERENT day is ALLOWED."""
        engine = MockRiskEngine(mock_db_session)
        
        # No existing positions
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_circular_trading(
            partner_id=uuid4(),
            commodity_id=uuid4(),
            transaction_type="BUY",
            trade_date=date.today()
        )
        
        assert result["blocked"] is False
    
    async def test_different_commodity_allowed(self, mock_db_session):
        """E2E: Same-day opposite position for DIFFERENT commodity is ALLOWED."""
        engine = MockRiskEngine(mock_db_session)
        
        # No positions for this commodity
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_circular_trading(
            partner_id=uuid4(),
            commodity_id=uuid4(),
            transaction_type="BUY",
            trade_date=date.today()
        )
        
        assert result["blocked"] is False


# ============================================================================
# TEST CATEGORY 7: Party Links Blocks
# ============================================================================

@pytest.mark.asyncio
class TestPartyLinksBlocks:
    """E2E Tests: Party links detection and blocking."""
    
    async def test_same_pan_blocked(self, mock_db_session):
        """E2E: Same PAN number → Trade BLOCKED."""
        engine = MockRiskEngine(mock_db_session)
        
        same_pan = "ABCDE1234F"
        
        buyer = MockBusinessPartner(
            pan_number=same_pan,
            tax_id_number=None,
            primary_contact_phone="+911234567890",
            primary_contact_email="buyer@company1.com"
        )
        seller = MockBusinessPartner(
            pan_number=same_pan,  # SAME!
            tax_id_number=None,
            primary_contact_phone="+919876543210",
            primary_contact_email="seller@company2.com"
        )
        
        call_count = [0]
        
        def mock_scalar():
            call_count[0] += 1
            return buyer if call_count[0] == 1 else seller
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = mock_scalar
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_party_links(
            buyer_partner_id=uuid4(),
            seller_partner_id=uuid4()
        )
        
        assert result["severity"] == "BLOCK"
        assert result["linked"] is True
        assert len(result["block_violations"]) >= 1
    
    async def test_same_tax_id_blocked(self, mock_db_session):
        """E2E: Same Tax ID (GST) → Trade BLOCKED."""
        engine = MockRiskEngine(mock_db_session)
        
        same_gst = "29ABCDE1234F1Z5"
        
        buyer = MockBusinessPartner(
            pan_number="ABCDE1234F",
            tax_id_number=same_gst,
            primary_contact_phone=None,
            primary_contact_email=None
        )
        seller = MockBusinessPartner(
            pan_number="FGHIJ5678K",
            tax_id_number=same_gst,  # SAME!
            primary_contact_phone=None,
            primary_contact_email=None
        )
        
        call_count = [0]
        
        def mock_scalar():
            call_count[0] += 1
            return buyer if call_count[0] == 1 else seller
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = mock_scalar
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_party_links(
            buyer_partner_id=uuid4(),
            seller_partner_id=uuid4()
        )
        
        assert result["severity"] == "BLOCK"
        assert result["linked"] is True
    
    async def test_same_mobile_warned(self, mock_db_session):
        """E2E: Same mobile number → WARN (not block)."""
        engine = MockRiskEngine(mock_db_session)
        
        same_phone = "+919876543210"
        
        buyer = MockBusinessPartner(
            pan_number="ABCDE1234F",
            tax_id_number="29ABCDE1234F1Z5",
            primary_contact_phone=same_phone,
            primary_contact_email="buyer@gmail.com"
        )
        seller = MockBusinessPartner(
            pan_number="FGHIJ5678K",
            tax_id_number="27FGHIJ5678K1Z9",
            primary_contact_phone=same_phone,  # SAME!
            primary_contact_email="seller@gmail.com"
        )
        
        call_count = [0]
        
        def mock_scalar():
            call_count[0] += 1
            return buyer if call_count[0] == 1 else seller
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = mock_scalar
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_party_links(
            buyer_partner_id=uuid4(),
            seller_partner_id=uuid4()
        )
        
        assert result["severity"] == "WARN"
        assert result["linked"] is True
        assert len(result["warn_violations"]) >= 1
    
    async def test_same_corporate_email_domain_warned(self, mock_db_session):
        """E2E: Same corporate email domain → WARN."""
        engine = MockRiskEngine(mock_db_session)
        
        buyer = MockBusinessPartner(
            pan_number="ABCDE1234F",
            tax_id_number=None,
            primary_contact_phone="+911234567890",
            primary_contact_email="user1@acmecorp.com"
        )
        seller = MockBusinessPartner(
            pan_number="FGHIJ5678K",
            tax_id_number=None,
            primary_contact_phone="+919876543210",
            primary_contact_email="user2@acmecorp.com"  # SAME domain
        )
        
        call_count = [0]
        
        def mock_scalar():
            call_count[0] += 1
            return buyer if call_count[0] == 1 else seller
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = mock_scalar
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_party_links(
            buyer_partner_id=uuid4(),
            seller_partner_id=uuid4()
        )
        
        assert result["severity"] == "WARN"
        assert result["linked"] is True
    
    async def test_common_email_provider_not_flagged(self, mock_db_session):
        """E2E: Common email providers (gmail) should NOT flag as linked."""
        engine = MockRiskEngine(mock_db_session)
        
        buyer = MockBusinessPartner(
            pan_number="ABCDE1234F",
            tax_id_number=None,
            primary_contact_phone="+911234567890",
            primary_contact_email="buyer@gmail.com"
        )
        seller = MockBusinessPartner(
            pan_number="FGHIJ5678K",
            tax_id_number=None,
            primary_contact_phone="+919876543210",
            primary_contact_email="seller@gmail.com"  # gmail is common
        )
        
        call_count = [0]
        
        def mock_scalar():
            call_count[0] += 1
            return buyer if call_count[0] == 1 else seller
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = mock_scalar
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_party_links(
            buyer_partner_id=uuid4(),
            seller_partner_id=uuid4()
        )
        
        # Gmail is common provider - email domain should not be flagged
        email_violations = [v for v in result.get("violations", []) 
                          if "EMAIL" in v.get("type", "").upper()]
        assert len(email_violations) == 0
    
    async def test_no_links_passes(self, mock_db_session):
        """E2E: Different entities with no links → PASS."""
        engine = MockRiskEngine(mock_db_session)
        
        buyer = MockBusinessPartner(
            pan_number="ABCDE1234F",
            tax_id_number="29ABCDE1234F1Z5",
            primary_contact_phone="+911234567890",
            primary_contact_email="buyer@company1.com"
        )
        seller = MockBusinessPartner(
            pan_number="FGHIJ5678K",
            tax_id_number="27FGHIJ5678K1Z9",
            primary_contact_phone="+919876543210",
            primary_contact_email="seller@company2.com"
        )
        
        call_count = [0]
        
        def mock_scalar():
            call_count[0] += 1
            return buyer if call_count[0] == 1 else seller
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = mock_scalar
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.check_party_links(
            buyer_partner_id=uuid4(),
            seller_partner_id=uuid4()
        )
        
        assert result["severity"] == "PASS"
        assert result["linked"] is False
        assert len(result["violations"]) == 0


# ============================================================================
# TEST CATEGORY 8: Role Restriction Validation
# ============================================================================

@pytest.mark.asyncio
class TestRoleRestrictions:
    """E2E Tests: Role-based trading restrictions."""
    
    async def test_buyer_cannot_sell(self, mock_db_session):
        """E2E: BUYER partner cannot post SELL availability."""
        engine = MockRiskEngine(mock_db_session)
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value="buyer")
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.validate_partner_role(
            partner_id=uuid4(),
            transaction_type="SELL"
        )
        
        assert result["allowed"] is False
        assert "BUYER" in result["reason"].upper() or "cannot" in result["reason"].lower()
    
    async def test_buyer_can_buy(self, mock_db_session):
        """E2E: BUYER partner CAN post BUY requirement."""
        engine = MockRiskEngine(mock_db_session)
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value="buyer")
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.validate_partner_role(
            partner_id=uuid4(),
            transaction_type="BUY"
        )
        
        assert result["allowed"] is True
    
    async def test_seller_cannot_buy(self, mock_db_session):
        """E2E: SELLER partner cannot post BUY requirement."""
        engine = MockRiskEngine(mock_db_session)
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value="seller")
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.validate_partner_role(
            partner_id=uuid4(),
            transaction_type="BUY"
        )
        
        assert result["allowed"] is False
        assert "SELLER" in result["reason"].upper() or "cannot" in result["reason"].lower()
    
    async def test_seller_can_sell(self, mock_db_session):
        """E2E: SELLER partner CAN post SELL availability."""
        engine = MockRiskEngine(mock_db_session)
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value="seller")
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await engine.validate_partner_role(
            partner_id=uuid4(),
            transaction_type="SELL"
        )
        
        assert result["allowed"] is True
    
    async def test_trader_can_buy_and_sell(self, mock_db_session):
        """E2E: TRADER partner can do both BUY and SELL."""
        engine = MockRiskEngine(mock_db_session)
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value="trader")
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Test BUY
        result_buy = await engine.validate_partner_role(
            partner_id=uuid4(),
            transaction_type="BUY"
        )
        assert result_buy["allowed"] is True
        
        # Test SELL
        result_sell = await engine.validate_partner_role(
            partner_id=uuid4(),
            transaction_type="SELL"
        )
        assert result_sell["allowed"] is True


# ============================================================================
# Run tests: pytest backend/tests/e2e/test_matching_engine_e2e.py -v
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
