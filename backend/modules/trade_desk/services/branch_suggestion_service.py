"""
Branch Suggestion Service - AI-Powered Branch Selection for Trades

Scoring Algorithm (100 points total):
1. State Match (40 points) - Same state = avoid IGST
2. Distance (30 points) - Closer = faster delivery
3. Capacity (20 points) - Enough warehouse space
4. Commodity Support (10 points) - Handles this commodity

Returns ranked list of branches with scores and reasoning.
User can accept AI suggestion or override with manual selection.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
import math

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.partners.repositories.branch_repository import BranchRepository
from backend.modules.partners.models import PartnerBranch


class BranchSuggestionService:
    """
    AI scoring for optimal branch selection.
    
    Used when partner has multiple branches - suggests best match
    based on trade requirements.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        branch_repo: BranchRepository
    ):
        self.db = db
        self.branch_repo = branch_repo
    
    async def suggest_ship_to_branch(
        self,
        partner_id: UUID,
        commodity_code: str,
        quantity_qtls: int,
        target_state: str,
        target_latitude: Optional[Decimal] = None,
        target_longitude: Optional[Decimal] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest best ship-to branch for buyer.
        
        Args:
            partner_id: Buyer partner UUID
            commodity_code: Commodity code
            quantity_qtls: Required quantity
            target_state: Seller's state (for GST matching)
            target_latitude: Seller's latitude (for distance)
            target_longitude: Seller's longitude (for distance)
        
        Returns:
            List of dicts with:
                - branch: PartnerBranch object
                - score: Total score (0-100)
                - reasoning: Why this score
                - breakdown: Score components
        """
        # Get eligible branches
        branches = await self.branch_repo.get_ship_to_branches(
            partner_id=partner_id,
            commodity_code=commodity_code,
            required_capacity_qtls=quantity_qtls
        )
        
        if not branches:
            return []
        
        # Score each branch
        suggestions = []
        for branch in branches:
            score_data = await self._score_branch(
                branch=branch,
                target_state=target_state,
                target_lat=target_latitude,
                target_long=target_longitude,
                required_capacity=quantity_qtls
            )
            
            suggestions.append({
                'branch': branch,
                'score': score_data['total_score'],
                'reasoning': score_data['reasoning'],
                'breakdown': score_data['breakdown']
            })
        
        # Sort by score descending
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        
        return suggestions
    
    async def suggest_ship_from_branch(
        self,
        partner_id: UUID,
        commodity_code: str,
        target_state: str,
        target_latitude: Optional[Decimal] = None,
        target_longitude: Optional[Decimal] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest best ship-from branch for seller.
        
        Similar to ship_to but for seller's dispatch address.
        """
        branches = await self.branch_repo.get_ship_from_branches(
            partner_id=partner_id,
            commodity_code=commodity_code
        )
        
        if not branches:
            return []
        
        suggestions = []
        for branch in branches:
            score_data = await self._score_branch(
                branch=branch,
                target_state=target_state,
                target_lat=target_latitude,
                target_long=target_longitude,
                required_capacity=None  # Not relevant for ship-from
            )
            
            suggestions.append({
                'branch': branch,
                'score': score_data['total_score'],
                'reasoning': score_data['reasoning'],
                'breakdown': score_data['breakdown']
            })
        
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        
        return suggestions
    
    async def _score_branch(
        self,
        branch: PartnerBranch,
        target_state: str,
        target_lat: Optional[Decimal],
        target_long: Optional[Decimal],
        required_capacity: Optional[int]
    ) -> Dict[str, Any]:
        """
        Score a single branch (0-100 points).
        
        Returns:
            Dict with total_score, reasoning, breakdown
        """
        scores = {}
        reasoning_parts = []
        
        # === 1. STATE MATCH (40 points) ===
        if branch.state == target_state:
            scores['state_match'] = 40
            reasoning_parts.append(
                f"✓ Same state ({branch.state}) - CGST+SGST instead of IGST"
            )
        else:
            scores['state_match'] = 0
            reasoning_parts.append(
                f"✗ Different state ({branch.state} vs {target_state}) - IGST applicable"
            )
        
        # === 2. DISTANCE (30 points) ===
        if target_lat and target_long and branch.latitude and branch.longitude:
            distance_km = await self.branch_repo.calculate_distance(
                branch.id, target_lat, target_long
            )
            
            if distance_km is not None:
                # Scoring: 30 points at 0km, 0 points at 500km+
                # Linear decrease
                distance_score = max(0, 30 - (distance_km / 500 * 30))
                scores['distance'] = round(distance_score, 2)
                reasoning_parts.append(
                    f"Distance: {distance_km:.0f} km → {distance_score:.0f} points"
                )
            else:
                scores['distance'] = 15  # Neutral if calculation fails
        else:
            scores['distance'] = 15  # Neutral if no coordinates
            reasoning_parts.append("Distance: Coordinates not available")
        
        # === 3. CAPACITY (20 points) ===
        if required_capacity and branch.warehouse_capacity_qtls:
            available = await self.branch_repo.get_available_capacity(branch.id)
            
            if available and available >= required_capacity:
                # Full points if capacity sufficient
                utilization = required_capacity / available
                if utilization <= 0.8:  # <80% utilization
                    scores['capacity'] = 20
                    reasoning_parts.append(
                        f"✓ Capacity: {available} qtls available (need {required_capacity})"
                    )
                else:
                    scores['capacity'] = 15  # Tight but ok
                    reasoning_parts.append(
                        f"⚠ Capacity: {available} qtls available (need {required_capacity}) - tight"
                    )
            else:
                scores['capacity'] = 0
                reasoning_parts.append(
                    f"✗ Insufficient capacity: {available or 0} qtls (need {required_capacity})"
                )
        else:
            scores['capacity'] = 10  # Neutral if no capacity tracking
            reasoning_parts.append("Capacity: Not tracked for this branch")
        
        # === 4. COMMODITY SUPPORT (10 points) ===
        # Already filtered in get_ship_to_branches, so if we're here, it's supported
        scores['commodity_support'] = 10
        reasoning_parts.append("✓ Commodity supported")
        
        # === TOTAL ===
        total = sum(scores.values())
        
        return {
            'total_score': round(total, 2),
            'reasoning': ' | '.join(reasoning_parts),
            'breakdown': scores
        }
