"""
Test Anonymous Matching with Match Tokens

Validates that:
1. Match results hide party identities (show tokens instead)
2. Match tokens are created automatically
3. Region info is anonymized (state only, not city)
4. Privacy notice is included in response
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from decimal import Decimal

from backend.modules.trade_desk.models.match_token import MatchToken
from backend.modules.trade_desk.schemas.anonymous_match_response import (
    AnonymousMatchResponse,
    AnonymousFindMatchesResponse,
    AnonymousMatchScoreBreakdown
)


class TestMatchToken:
    """Test MatchToken model"""
    
    def test_token_generation(self):
        """Test that tokens are auto-generated"""
        token = MatchToken(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score="0.85"
        )
        
        assert token.token is not None
        assert token.token.startswith("MATCH-")
        assert len(token.token) == 11  # MATCH-XXXXX (11 chars)
    
    def test_token_uniqueness(self):
        """Test that generated tokens are unique"""
        tokens = set()
        for _ in range(100):
            token = MatchToken(
                requirement_id=uuid4(),
                availability_id=uuid4(),
                match_score="0.75"
            )
            tokens.add(token.token)
        
        # Should generate 100 unique tokens
        assert len(tokens) == 100
    
    def test_default_disclosure_level(self):
        """Test default disclosure is MATCHED (anonymous)"""
        token = MatchToken(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score="0.90"
        )
        
        assert token.disclosed_to_buyer == "MATCHED"
        assert token.disclosed_to_seller == "MATCHED"
        assert token.negotiation_started_at is None
    
    def test_reveal_to_buyer(self):
        """Test revealing seller identity to buyer"""
        token = MatchToken(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score="0.88"
        )
        
        assert token.disclosed_to_buyer == "MATCHED"
        
        token.reveal_to_buyer()
        
        assert token.disclosed_to_buyer == "NEGOTIATING"
        assert token.negotiation_started_at is not None
    
    def test_reveal_to_seller(self):
        """Test revealing buyer identity to seller"""
        token = MatchToken(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score="0.92"
        )
        
        assert token.disclosed_to_seller == "MATCHED"
        
        token.reveal_to_seller()
        
        assert token.disclosed_to_seller == "NEGOTIATING"
        assert token.negotiation_started_at is not None
    
    def test_mark_traded(self):
        """Test marking as traded (full disclosure)"""
        token = MatchToken(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score="0.95"
        )
        
        token.mark_traded()
        
        assert token.disclosed_to_buyer == "TRADE"
        assert token.disclosed_to_seller == "TRADE"
    
    def test_token_expiration(self):
        """Test token expiration logic"""
        token = MatchToken(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score="0.70"
        )
        
        # Should expire in 30 days
        assert token.expires_at is not None
        assert not token.is_expired
        
        # Force expiration
        token.expires_at = datetime.utcnow() - timedelta(days=1)
        assert token.is_expired
    
    def test_is_negotiating(self):
        """Test negotiation status check"""
        token = MatchToken(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            match_score="0.82"
        )
        
        assert not token.is_negotiating
        
        token.reveal_to_buyer()
        
        assert token.is_negotiating


class TestAnonymousMatchResponse:
    """Test AnonymousMatchResponse schema"""
    
    def test_anonymous_response_schema(self):
        """Test that response hides party IDs"""
        response = AnonymousMatchResponse(
            match_token="MATCH-A7B2C",
            score=0.85,
            base_score=0.80,
            warn_penalty_applied=True,
            warn_penalty_value=0.05,
            ai_boost_applied=False,
            ai_boost_value=0.0,
            ai_recommended=False,
            risk_status="PASS",
            risk_score=75,
            score_breakdown=AnonymousMatchScoreBreakdown(
                quality_score=0.9,
                price_score=0.8,
                delivery_score=0.85,
                risk_score=0.75
            ),
            recommendations="Good match with acceptable risk",
            counterparty_region="North Gujarat",
            counterparty_rating=4.5,
            matched_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            disclosure_level="MATCHED"
        )
        
        # Verify NO party IDs exposed
        response_dict = response.model_dump()
        assert 'requirement_id' not in response_dict
        assert 'availability_id' not in response_dict
        assert 'seller_partner_id' not in response_dict
        assert 'buyer_partner_id' not in response_dict
        
        # Verify anonymous token present
        assert response.match_token == "MATCH-A7B2C"
        
        # Verify region anonymization (state only)
        assert response.counterparty_region == "North Gujarat"
        
        # Verify disclosure level
        assert response.disclosure_level == "MATCHED"
    
    def test_anonymous_find_matches_response(self):
        """Test find matches response includes privacy notice"""
        response = AnonymousFindMatchesResponse(
            matches=[],
            total_found=0,
            request_id=uuid4(),
            commodity_code="COTTON",
            min_score_threshold=0.7,
            ai_integration_enabled=True
        )
        
        # Should include privacy notice
        assert "Identities are hidden" in response.privacy_notice
        assert "Start Negotiation" in response.privacy_notice


class TestPrivacyProtection:
    """Test privacy protection mechanisms"""
    
    def test_no_identity_leakage_in_match_response(self):
        """Verify NO identity information leaks in match responses"""
        match = AnonymousMatchResponse(
            match_token="MATCH-X9Y4Z",
            score=0.92,
            base_score=0.90,
            warn_penalty_applied=False,
            warn_penalty_value=0.0,
            ai_boost_applied=True,
            ai_boost_value=0.02,
            ai_recommended=True,
            risk_status="PASS",
            risk_score=85,
            score_breakdown=AnonymousMatchScoreBreakdown(
                quality_score=0.95,
                price_score=0.88,
                delivery_score=0.92,
                risk_score=0.85
            ),
            recommendations="Excellent match, AI recommended",
            counterparty_region="West Maharashtra",
            counterparty_rating=4.8,
            matched_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            disclosure_level="MATCHED"
        )
        
        data = match.model_dump()
        
        # Check NO sensitive fields
        forbidden_fields = [
            'requirement_id', 'availability_id',
            'buyer_partner_id', 'seller_partner_id',
            'buyer_name', 'seller_name',
            'city', 'address', 'phone', 'email'
        ]
        
        for field in forbidden_fields:
            assert field not in data, f"Privacy violation: {field} exposed"
        
        # Verify only safe fields present
        assert data['match_token'] == "MATCH-X9Y4Z"
        assert data['counterparty_region'] == "West Maharashtra"
        assert data['disclosure_level'] == "MATCHED"
    
    def test_region_anonymization(self):
        """Test that location is anonymized to region only"""
        # Should show state/region, NOT city or exact address
        response = AnonymousMatchResponse(
            match_token="MATCH-B3D5F",
            score=0.78,
            base_score=0.75,
            warn_penalty_applied=False,
            warn_penalty_value=0.0,
            score_breakdown=AnonymousMatchScoreBreakdown(
                quality_score=0.8,
                price_score=0.75,
                delivery_score=0.78,
                risk_score=0.78
            ),
            recommendations="Acceptable match",
            counterparty_region="South Gujarat",  # State/region only
            matched_at=datetime.utcnow(),
            disclosure_level="MATCHED"
        )
        
        # Region should be general (state level)
        assert response.counterparty_region == "South Gujarat"
        
        # Should NOT contain city names
        assert "Surat" not in (response.counterparty_region or "")
        assert "Ahmedabad" not in (response.counterparty_region or "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
