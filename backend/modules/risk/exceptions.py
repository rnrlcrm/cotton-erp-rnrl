"""
Risk Engine Exceptions

Custom exceptions for risk assessment and validation failures.
"""


class RiskCheckFailedError(Exception):
    """
    Raised when risk assessment fails and entity should be blocked.
    
    Used in:
    - RequirementService.create_requirement()
    - AvailabilityService.create_availability()
    - MatchingService (peer-to-peer filtering)
    
    Example:
        if risk_result["status"] == "FAIL":
            raise RiskCheckFailedError(
                f"Risk check failed: {risk_result['reason']}. "
                f"Score: {risk_result['score']}/100"
            )
    """
    def __init__(self, message: str, risk_details: dict = None):
        self.message = message
        self.risk_details = risk_details or {}
        super().__init__(self.message)


class CircularTradingViolation(RiskCheckFailedError):
    """Raised when circular trading is detected (unsettled position exists)."""
    pass


class WashTradingViolation(RiskCheckFailedError):
    """Raised when wash trading is detected (same-party reverse trade same day)."""
    pass


class PartyLinkViolation(RiskCheckFailedError):
    """Raised when party links are detected (same PAN/GST)."""
    pass


class PeerRelationshipBlockedError(RiskCheckFailedError):
    """Raised when peer-to-peer relationship score is too low (<30)."""
    pass
