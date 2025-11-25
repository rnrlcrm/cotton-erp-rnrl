"""
Trade Desk Matching Engine Module

Intelligent bilateral matching system with:
- Location-first hard filtering
- Multi-factor scoring (quality/price/delivery/risk)
- Event-driven real-time triggers  
- Atomic partial allocation
- Duplicate detection
"""

from .matching_engine import MatchingEngine, MatchResult
from .scoring import MatchScorer
from .validators import MatchValidator

__all__ = [
    "MatchingEngine",
    "MatchResult",
    "MatchScorer",
    "MatchValidator",
]
