"""
Trade Desk Models
"""

# Import order matters for SQLAlchemy relationship resolution
# MatchToken must be imported before Availability since Availability references it
from backend.modules.trade_desk.models.match_token import MatchToken
from backend.modules.trade_desk.models.availability_embedding import AvailabilityEmbedding
from backend.modules.trade_desk.models.requirement_embedding import RequirementEmbedding
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.match_outcome import MatchOutcome
from backend.modules.trade_desk.models.negotiation import Negotiation
from backend.modules.trade_desk.models.negotiation_offer import NegotiationOffer
from backend.modules.trade_desk.models.negotiation_message import NegotiationMessage
from backend.modules.trade_desk.models.trade import Trade
from backend.modules.trade_desk.models.trade_signature import TradeSignature
from backend.modules.trade_desk.models.trade_amendment import TradeAmendment

__all__ = [
    "Availability",
    "Requirement",
    "AvailabilityEmbedding",
    "RequirementEmbedding",
    "MatchOutcome",
    "MatchToken",
    "Negotiation",
    "NegotiationOffer",
    "NegotiationMessage",
    "Trade",
    "TradeSignature",
    "TradeAmendment",
]
