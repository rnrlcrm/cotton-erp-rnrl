"""
Test AI Memory Loader

Tests for conversation history and context loading.
"""

import pytest
from uuid import uuid4
from backend.ai.memory.loader import AIMemoryLoader


@pytest.mark.asyncio
async def test_load_user_preferences(db_session):
    """Test loading user preferences."""
    from backend.modules.user_onboarding.models import User, PartnerType
    
    # Create test user
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        mobile_number="+919876543210",
        preferred_language="hi",
        partner_type=PartnerType.FARMER,
    )
    db_session.add(user)
    await db_session.commit()
    
    # Load preferences
    loader = AIMemoryLoader(db_session)
    prefs = await loader.load_user_preferences(user.id)
    
    assert prefs["name"] == "Test User"
    assert prefs["language"] == "hi"
    assert prefs["partner_type"] == "FARMER"
    assert prefs["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_load_recent_trades(db_session):
    """Test loading recent trade activity."""
    from backend.modules.user_onboarding.models import User
    from backend.modules.trade_desk.models.requirement import Requirement, RequirementStatus
    from backend.modules.trade_desk.models.commodity import Commodity
    
    # Create test user
    user = User(id=uuid4(), name="Trader", email="trader@example.com", mobile_number="+919876543210")
    db_session.add(user)
    
    # Create commodity
    commodity = Commodity(id=uuid4(), name="Cotton", code="CTN")
    db_session.add(commodity)
    
    # Create requirements
    for i in range(3):
        req = Requirement(
            id=uuid4(),
            created_by_id=user.id,
            commodity_id=commodity.id,
            quantity=100 + i,
            status=RequirementStatus.ACTIVE,
        )
        db_session.add(req)
    
    await db_session.commit()
    
    # Load recent trades
    loader = AIMemoryLoader(db_session)
    trades = await loader.load_recent_trades(user.id, limit=5)
    
    assert len(trades) == 3
    assert trades[0]["type"] == "requirement"
    assert trades[0]["commodity"] == "Cotton"


@pytest.mark.asyncio
async def test_load_context(db_session):
    """Test loading complete AI context."""
    from backend.modules.user_onboarding.models import User, PartnerType
    
    # Create test user
    user = User(
        id=uuid4(),
        name="Context User",
        email="context@example.com",
        mobile_number="+919876543210",
        preferred_language="en",
        partner_type=PartnerType.TRADER,
    )
    db_session.add(user)
    await db_session.commit()
    
    # Load context
    loader = AIMemoryLoader(db_session)
    context = await loader.load_context(user.id)
    
    assert context["user_id"] == str(user.id)
    assert "preferences" in context
    assert "summary" in context
    
    # Check summary
    assert "Context User" in context["summary"]
    assert "TRADER" in context["summary"]


@pytest.mark.asyncio
async def test_generate_summary(db_session):
    """Test summary generation."""
    loader = AIMemoryLoader(db_session)
    
    context = {
        "preferences": {
            "name": "Farmer Joe",
            "partner_type": "FARMER",
            "language": "hi",
        },
        "recent_trades": [
            {"type": "availability", "commodity": "Cotton"},
            {"type": "availability", "commodity": "Wheat"},
        ],
    }
    
    summary = loader._generate_summary(context)
    
    assert "Farmer Joe" in summary
    assert "FARMER" in summary
    assert "Cotton" in summary or "Wheat" in summary
