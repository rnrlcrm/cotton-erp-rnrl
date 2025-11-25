"""
Matching Engine Configuration

Per-commodity configurable parameters for intelligent matching.
Runtime-tunable via admin settings.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class MatchingConfig:
    """
    Configuration for matching engine behavior.
    
    Supports per-commodity customization for:
    - Scoring weights (quality/price/delivery/risk)
    - Minimum score thresholds
    - Duplicate detection tolerances
    - Notification settings
    - Performance tuning
    """
    
    # ========================================================================
    # SCORING WEIGHTS (Per-Commodity Configurable)
    # ========================================================================
    
    SCORING_WEIGHTS: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "default": {
            "quality": 0.40,
            "price": 0.30,
            "delivery": 0.15,
            "risk": 0.15
        },
        # Example commodity overrides
        "COTTON": {
            "quality": 0.40,
            "price": 0.30,
            "delivery": 0.15,
            "risk": 0.15
        },
        "GOLD": {
            "quality": 0.30,
            "price": 0.40,  # Price more critical for precious metals
            "delivery": 0.10,
            "risk": 0.20  # Higher risk scrutiny
        },
        "WHEAT": {
            "quality": 0.35,
            "price": 0.35,
            "delivery": 0.20,  # Logistics important for grains
            "risk": 0.10
        },
        "RICE": {
            "quality": 0.35,
            "price": 0.35,
            "delivery": 0.20,
            "risk": 0.10
        },
        "OIL": {
            "quality": 0.40,
            "price": 0.35,
            "delivery": 0.15,
            "risk": 0.10
        }
    })
    
    # ========================================================================
    # MIN SCORE THRESHOLD (Per-Commodity Configurable)
    # ========================================================================
    
    MIN_SCORE_THRESHOLD: Dict[str, float] = field(default_factory=lambda: {
        "default": 0.6,  # 60% match minimum
        "COTTON": 0.6,
        "GOLD": 0.7,  # Higher bar for precious metals
        "WHEAT": 0.5,  # More lenient for grains
        "RICE": 0.5,
        "OIL": 0.6
    })
    
    # ========================================================================
    # DUPLICATE DETECTION
    # ========================================================================
    
    DUPLICATE_TIME_WINDOW_MINUTES: int = 5
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.95  # 95% param match
    
    # ========================================================================
    # NOTIFICATION SETTINGS
    # ========================================================================
    
    MAX_MATCHES_TO_NOTIFY: int = 5  # Top N only
    NOTIFICATION_RATE_LIMIT_SECONDS: int = 60  # Max 1 per user per minute
    
    # ========================================================================
    # PARTIAL MATCHING
    # ========================================================================
    
    ENABLE_PARTIAL_MATCHING: bool = True
    MIN_PARTIAL_QUANTITY_PERCENT: float = 0.10  # Minimum 10% of required qty
    
    # ========================================================================
    # PERFORMANCE TUNING
    # ========================================================================
    
    MATCH_BATCH_SIZE: int = 100  # For high-volume scenarios
    MATCH_BATCH_DELAY_MS: int = 1000  # 1s micro-batching
    MAX_CONCURRENT_MATCHES: int = 50  # Max results per search
    
    # ========================================================================
    # RISK WARN PENALTY
    # ========================================================================
    
    RISK_WARN_GLOBAL_PENALTY: float = 0.10  # -10% to final score
    
    # ========================================================================
    # LOCATION MATCHING
    # ========================================================================
    
    ALLOW_CROSS_STATE_MATCHING: bool = False  # Block cross-state by default
    ALLOW_SAME_STATE_MATCHING: bool = True
    MAX_DISTANCE_KM: Optional[float] = None  # None = no distance limit
    
    # ========================================================================
    # INTERNAL BRANCH TRADING
    # ========================================================================
    
    BLOCK_INTERNAL_BRANCH_TRADING: bool = True  # Prevent circular trades
    
    # ========================================================================
    # AI INTEGRATION SETTINGS (ENHANCEMENT #7)
    # ========================================================================
    
    MIN_AI_CONFIDENCE_THRESHOLD: int = 60  # Minimum AI confidence % (0-100)
    ENABLE_AI_PRICE_ALERTS: bool = True    # Honor AI price alerts in validation
    ENABLE_AI_RECOMMENDATIONS: bool = True  # Consider AI pre-scored sellers
    AI_PRICE_DEVIATION_WARN_PERCENT: float = 10.0  # Warn if >10% above AI price
    ENABLE_AI_SCORE_BOOST: bool = True     # Boost score for AI-recommended sellers
    AI_RECOMMENDATION_SCORE_BOOST: float = 0.05  # +5% boost for AI recommendations
    
    # ========================================================================
    # SAFETY CRON
    # ========================================================================
    
    SAFETY_CRON_INTERVAL_SECONDS: int = 30  # Fallback check interval
    ENABLE_SAFETY_CRON: bool = True
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def get_scoring_weights(self, commodity_code: str) -> Dict[str, float]:
        """
        Get scoring weights for a commodity.
        
        Args:
            commodity_code: Commodity code (e.g., "COTTON", "GOLD")
            
        Returns:
            Dictionary with quality/price/delivery/risk weights
        """
        return self.SCORING_WEIGHTS.get(
            commodity_code.upper(),
            self.SCORING_WEIGHTS["default"]
        )
    
    def get_min_score_threshold(self, commodity_code: str) -> float:
        """
        Get minimum score threshold for a commodity.
        
        Args:
            commodity_code: Commodity code
            
        Returns:
            Minimum match score (0.0-1.0)
        """
        return self.MIN_SCORE_THRESHOLD.get(
            commodity_code.upper(),
            self.MIN_SCORE_THRESHOLD["default"]
        )
    
    def validate_weights(self, commodity_code: str) -> bool:
        """
        Validate that scoring weights sum to 1.0.
        
        Args:
            commodity_code: Commodity code
            
        Returns:
            True if weights are valid
        """
        weights = self.get_scoring_weights(commodity_code)
        total = sum(weights.values())
        return abs(total - 1.0) < 0.001  # Allow small floating point errors


# Global instance (can be overridden for testing)
_matching_config = MatchingConfig()


def get_matching_config() -> MatchingConfig:
    """Get global matching configuration instance."""
    return _matching_config


def set_matching_config(config: MatchingConfig) -> None:
    """Set global matching configuration (for testing/runtime updates)."""
    global _matching_config
    _matching_config = config
