"""
Anonymization Service - Privacy layer for Trade Desk

Ensures user identities are hidden until negotiation starts.

Privacy Rules:
1. PRE-MATCH: All listings are anonymous (no partner IDs, names, locations revealed)
2. POST-MATCH: Only matched parties see each other's basic info
3. POST-NEGOTIATION: Full details shared between negotiating parties
4. BACK-OFFICE: Admin users see everything (compliance/audit)

Identity Disclosure Stages:
- Stage 0 (Browse): Anonymous listing (commodity, quality, approx region only)
- Stage 1 (Match): Match ID shared, no identity yet
- Stage 2 (Negotiation Start): Basic company name + city revealed
- Stage 3 (Deal Accepted): Full contact details shared
- Stage 4 (Trade): Complete party information
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from decimal import Decimal

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability


class AnonymizationService:
    """
    Privacy layer that anonymizes sensitive data based on user context.
    """
    
    @staticmethod
    def anonymize_location(
        location_id: Optional[UUID],
        location_address: Optional[str],
        location_region: Optional[str],
        disclosure_level: str = "NONE"
    ) -> Dict[str, Any]:
        """
        Anonymize location based on disclosure level.
        
        Args:
            location_id: Location UUID
            location_address: Full address
            location_region: Region/State
            disclosure_level: NONE | REGION | CITY | FULL
            
        Returns:
            Anonymized location data
        """
        if disclosure_level == "FULL":
            return {
                "location_id": location_id,
                "address": location_address,
                "region": location_region
            }
        elif disclosure_level == "CITY":
            # Extract only city from address
            city = location_address.split(",")[-2].strip() if location_address else None
            return {
                "location_id": None,
                "address": None,
                "city": city,
                "region": location_region
            }
        elif disclosure_level == "REGION":
            return {
                "location_id": None,
                "address": None,
                "city": None,
                "region": location_region or "India"
            }
        else:  # NONE
            return {
                "location_id": None,
                "address": None,
                "city": None,
                "region": "India"  # Country-level only
            }
    
    @staticmethod
    def anonymize_availability(
        availability: Availability,
        viewer_partner_id: UUID,
        disclosure_context: str = "BROWSE"
    ) -> Dict[str, Any]:
        """
        Anonymize availability based on disclosure context.
        
        Args:
            availability: Availability object
            viewer_partner_id: Who is viewing
            disclosure_context: BROWSE | MATCHED | NEGOTIATING | TRADE
            
        Returns:
            Anonymized availability data
        """
        is_own = availability.seller_partner_id == viewer_partner_id
        
        # Owner always sees full data
        if is_own:
            disclosure_context = "TRADE"
        
        # Base data (always visible)
        data = {
            "id": availability.id,
            "commodity_id": availability.commodity_id,
            "total_quantity": availability.total_quantity,
            "available_quantity": availability.available_quantity,
            "quantity_unit": availability.quantity_unit,
            "quality_params": availability.quality_params,
            "base_price": availability.base_price,
            "price_unit": availability.price_unit,
            "status": availability.status,
            "created_at": availability.created_at,
        }
        
        # Disclosure levels
        if disclosure_context == "BROWSE":
            # Anonymous browsing - NO identity
            data.update({
                "seller_partner_id": None,
                "seller_name": None,
                "seller_rating": None,
                "location": AnonymizationService.anonymize_location(
                    availability.location_id,
                    availability.delivery_address,
                    availability.delivery_region,
                    disclosure_level="REGION"
                ),
                "contact_info": None
            })
        
        elif disclosure_context == "MATCHED":
            # Matched but not negotiating - Region + approximate rating
            data.update({
                "seller_partner_id": None,  # Still hidden
                "seller_name": "Verified Seller",  # Generic
                "seller_rating": round(availability.seller_rating_score or 0, 1) if availability.seller_rating_score else None,
                "location": AnonymizationService.anonymize_location(
                    availability.location_id,
                    availability.delivery_address,
                    availability.delivery_region,
                    disclosure_level="CITY"  # City visible
                ),
                "contact_info": None
            })
        
        elif disclosure_context == "NEGOTIATING":
            # Negotiation started - Company name + city visible
            data.update({
                "seller_partner_id": None,  # Still hidden until deal
                "seller_name": availability.seller.name if availability.seller else "Verified Seller",
                "seller_rating": availability.seller_rating_score,
                "location": AnonymizationService.anonymize_location(
                    availability.location_id,
                    availability.delivery_address,
                    availability.delivery_region,
                    disclosure_level="CITY"
                ),
                "contact_info": {
                    "available_on_deal_acceptance": True
                }
            })
        
        else:  # TRADE (deal accepted)
            # Full disclosure
            data.update({
                "seller_partner_id": availability.seller_partner_id,
                "seller_name": availability.seller.name if availability.seller else None,
                "seller_rating": availability.seller_rating_score,
                "location": AnonymizationService.anonymize_location(
                    availability.location_id,
                    availability.delivery_address,
                    availability.delivery_region,
                    disclosure_level="FULL"
                ),
                "contact_info": {
                    "company_name": availability.seller.name if availability.seller else None,
                    "email": availability.seller.email if availability.seller else None,
                    "phone": availability.seller.phone if availability.seller else None,
                }
            })
        
        return data
    
    @staticmethod
    def anonymize_requirement(
        requirement: Requirement,
        viewer_partner_id: UUID,
        disclosure_context: str = "BROWSE"
    ) -> Dict[str, Any]:
        """
        Anonymize requirement based on disclosure context.
        
        Args:
            requirement: Requirement object
            viewer_partner_id: Who is viewing
            disclosure_context: BROWSE | MATCHED | NEGOTIATING | TRADE
            
        Returns:
            Anonymized requirement data
        """
        is_own = requirement.buyer_partner_id == viewer_partner_id
        
        # Owner always sees full data
        if is_own:
            disclosure_context = "TRADE"
        
        # Base data (always visible)
        data = {
            "id": requirement.id,
            "commodity_id": requirement.commodity_id,
            "min_quantity": requirement.min_quantity,
            "max_quantity": requirement.max_quantity,
            "quantity_unit": requirement.quantity_unit,
            "quality_requirements": requirement.quality_requirements,
            "max_budget_per_unit": requirement.max_budget_per_unit,
            "status": requirement.status,
            "created_at": requirement.created_at,
        }
        
        # Disclosure levels (same as availability)
        if disclosure_context == "BROWSE":
            data.update({
                "buyer_partner_id": None,
                "buyer_name": None,
                "buyer_rating": None,
                "delivery_locations": ["Region: India"],  # Country-level only
                "contact_info": None
            })
        
        elif disclosure_context == "MATCHED":
            data.update({
                "buyer_partner_id": None,
                "buyer_name": "Verified Buyer",
                "buyer_rating": round(requirement.buyer_rating_score or 0, 1) if requirement.buyer_rating_score else None,
                "delivery_locations": [f"City: {loc.get('city', 'India')}" for loc in (requirement.delivery_locations or [])],
                "contact_info": None
            })
        
        elif disclosure_context == "NEGOTIATING":
            data.update({
                "buyer_partner_id": None,
                "buyer_name": requirement.buyer_partner.name if requirement.buyer_partner else "Verified Buyer",
                "buyer_rating": requirement.buyer_rating_score,
                "delivery_locations": requirement.delivery_locations,
                "contact_info": {
                    "available_on_deal_acceptance": True
                }
            })
        
        else:  # TRADE
            data.update({
                "buyer_partner_id": requirement.buyer_partner_id,
                "buyer_name": requirement.buyer_partner.name if requirement.buyer_partner else None,
                "buyer_rating": requirement.buyer_rating_score,
                "delivery_locations": requirement.delivery_locations,
                "contact_info": {
                    "company_name": requirement.buyer_partner.name if requirement.buyer_partner else None,
                    "email": requirement.buyer_partner.email if requirement.buyer_partner else None,
                    "phone": requirement.buyer_partner.phone if requirement.buyer_partner else None,
                }
            })
        
        return data
    
    @staticmethod
    def can_view_match(
        match_requirement_id: UUID,
        match_availability_id: UUID,
        viewer_partner_id: UUID,
        requirement: Requirement,
        availability: Availability
    ) -> bool:
        """
        Check if user can view match details.
        
        Only matched parties can see match results.
        """
        is_buyer = requirement.buyer_partner_id == viewer_partner_id
        is_seller = availability.seller_partner_id == viewer_partner_id
        
        return is_buyer or is_seller
    
    @staticmethod
    def get_disclosure_context(
        viewer_partner_id: UUID,
        requirement: Optional[Requirement] = None,
        availability: Optional[Availability] = None,
        negotiation_status: Optional[str] = None,
        trade_status: Optional[str] = None
    ) -> str:
        """
        Determine disclosure context based on relationship.
        
        Returns: BROWSE | MATCHED | NEGOTIATING | TRADE
        """
        # If trade exists and accepted/completed
        if trade_status in ["ACTIVE", "COMPLETED"]:
            return "TRADE"
        
        # If negotiation is active
        if negotiation_status in ["IN_PROGRESS", "ACCEPTED"]:
            return "NEGOTIATING"
        
        # If matched but not negotiating
        if negotiation_status == "INITIATED":
            return "MATCHED"
        
        # Default: browsing
        return "BROWSE"
