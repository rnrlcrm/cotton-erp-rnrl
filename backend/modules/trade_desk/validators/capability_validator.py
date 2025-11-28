"""
Trade Desk Capability Validator

Validates partner capabilities for trade desk operations (availability posting, requirement posting, matching).

CRITICAL RULES:
1. Availability (Sell) Posting:
   - Indian entities: Must have domestic_sell_india=True
   - Foreign entities: Must have domestic_sell_home_country=True AND be posting in home country
   - Service providers: CANNOT post availabilities (blocked)

2. Requirement (Buy) Posting:
   - Indian entities: Must have domestic_buy_india=True
   - Foreign entities: Must have domestic_buy_home_country=True AND be posting in home country
   - Service providers: CANNOT post requirements (blocked)

3. Import/Export Trades:
   - Import from abroad: Buyer must have import_allowed=True
   - Export to abroad: Seller must have export_allowed=True

4. Location-Aware Validation:
   - Foreign entities can ONLY trade domestically in THEIR home country
   - Foreign entities CANNOT trade domestically in India (must establish Indian entity)

This validator prevents unauthorized trading before it reaches the trade desk.
"""

from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.modules.partners.models import BusinessPartner
from backend.modules.partners.repositories import BusinessPartnerRepository


class CapabilityValidationError(Exception):
    """Raised when partner lacks required capability."""
    
    def __init__(self, message: str, partner_id: UUID, required_capability: str):
        self.message = message
        self.partner_id = partner_id
        self.required_capability = required_capability
        super().__init__(message)


class TradeCapabilityValidator:
    """
    Validates trading capabilities for trade desk operations.
    
    Used by:
    - AvailabilityService.create_availability() - validate seller can sell
    - RequirementService.create_requirement() - validate buyer can buy
    - MatchValidator.validate_match_eligibility() - validate trade parties
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BusinessPartnerRepository(db)
    
    async def validate_sell_capability(
        self,
        partner_id: UUID,
        location_country: str,
        raise_exception: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that partner can post SELL availability.
        
        Rules:
        1. Service providers CANNOT sell (entity_class check)
        2. Indian entities need domestic_sell_india=True
        3. Foreign entities need domestic_sell_home_country=True AND location_country=partner.country
        4. For export, need export_allowed=True
        
        Args:
            partner_id: Partner UUID
            location_country: Country where goods are located
            raise_exception: If True, raise CapabilityValidationError on failure
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        
        Raises:
            CapabilityValidationError: If raise_exception=True and validation fails
        """
        partner = await self.repo.get_by_id(partner_id)
        
        if not partner:
            error_msg = f"❌ Partner {partner_id} not found"
            if raise_exception:
                raise CapabilityValidationError(error_msg, partner_id, "partner_exists")
            return False, error_msg
        
        # Rule 1: Service providers cannot trade
        if hasattr(partner, 'entity_class') and partner.entity_class == "service_provider":
            error_msg = (
                f"❌ CAPABILITY ERROR: Service providers cannot post sell availabilities\n"
                f"Partner: {partner.legal_name}\n"
                f"Entity Class: {partner.entity_class}\n"
                f"Reason: Service providers (brokers, transporters, etc.) are not allowed to trade"
            )
            if raise_exception:
                raise CapabilityValidationError(error_msg, partner_id, "entity_class")
            return False, error_msg
        
        # Get capabilities
        capabilities = partner.capabilities if hasattr(partner, 'capabilities') else {}
        
        # Rule 2: Indian domestic sell
        if partner.country == "India" and location_country == "India":
            can_sell = capabilities.get("domestic_sell_india", False)
            if not can_sell:
                error_msg = (
                    f"❌ CAPABILITY ERROR: Partner lacks permission to sell domestically in India\n"
                    f"Partner: {partner.legal_name}\n"
                    f"Country: {partner.country}\n"
                    f"Required Capability: domestic_sell_india\n"
                    f"Current Status: {can_sell}\n"
                    f"Action Required: Verify GST Certificate + PAN Card to enable selling"
                )
                if raise_exception:
                    raise CapabilityValidationError(error_msg, partner_id, "domestic_sell_india")
                return False, error_msg
            return True, None
        
        # Rule 3: Foreign domestic sell (CRITICAL RULE)
        if partner.country != "India" and location_country == partner.country:
            can_sell = capabilities.get("domestic_sell_home_country", False)
            if not can_sell:
                error_msg = (
                    f"❌ CAPABILITY ERROR: Partner lacks permission to sell in home country\n"
                    f"Partner: {partner.legal_name}\n"
                    f"Country: {partner.country}\n"
                    f"Required Capability: domestic_sell_home_country\n"
                    f"Current Status: {can_sell}\n"
                    f"Action Required: Verify foreign tax registration documents"
                )
                if raise_exception:
                    raise CapabilityValidationError(error_msg, partner_id, "domestic_sell_home_country")
                return False, error_msg
            return True, None
        
        # Rule 4: Foreign entity trying to sell in India (BLOCKED)
        if partner.country != "India" and location_country == "India":
            error_msg = (
                f"❌ CAPABILITY ERROR: Foreign entities CANNOT sell domestically in India\n"
                f"Partner: {partner.legal_name}\n"
                f"Partner Country: {partner.country}\n"
                f"Posting Location: {location_country}\n\n"
                f"⚠️ CRITICAL RULE VIOLATION:\n"
                f"Foreign entities can ONLY trade domestically in their home country.\n\n"
                f"To sell in India, you must:\n"
                f"1. Establish an Indian legal entity\n"
                f"2. Obtain Indian GST Certificate + PAN Card\n"
                f"3. Register as new Indian business partner\n\n"
                f"Alternative: Use export_allowed capability to sell TO India (international trade)"
            )
            if raise_exception:
                raise CapabilityValidationError(error_msg, partner_id, "domestic_sell_india")
            return False, error_msg
        
        # Rule 5: Export (international sell)
        if partner.country != location_country:
            can_export = capabilities.get("export_allowed", False)
            if not can_export:
                error_msg = (
                    f"❌ CAPABILITY ERROR: Partner lacks export permission\n"
                    f"Partner: {partner.legal_name}\n"
                    f"Partner Country: {partner.country}\n"
                    f"Goods Location: {location_country}\n"
                    f"Required Capability: export_allowed\n"
                    f"Current Status: {can_export}\n"
                    f"Action Required: Verify IEC + GST + PAN (India) OR Foreign Export License"
                )
                if raise_exception:
                    raise CapabilityValidationError(error_msg, partner_id, "export_allowed")
                return False, error_msg
            return True, None
        
        # Default: Allow (shouldn't reach here)
        return True, None
    
    async def validate_buy_capability(
        self,
        partner_id: UUID,
        delivery_country: str,
        raise_exception: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that partner can post BUY requirement.
        
        Rules:
        1. Service providers CANNOT buy
        2. Indian entities need domestic_buy_india=True
        3. Foreign entities need domestic_buy_home_country=True AND delivery_country=partner.country
        4. For import, need import_allowed=True
        
        Args:
            partner_id: Partner UUID
            delivery_country: Country where goods will be delivered
            raise_exception: If True, raise CapabilityValidationError on failure
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        
        Raises:
            CapabilityValidationError: If raise_exception=True and validation fails
        """
        partner = await self.repo.get_by_id(partner_id)
        
        if not partner:
            error_msg = f"❌ Partner {partner_id} not found"
            if raise_exception:
                raise CapabilityValidationError(error_msg, partner_id, "partner_exists")
            return False, error_msg
        
        # Rule 1: Service providers cannot trade
        if hasattr(partner, 'entity_class') and partner.entity_class == "service_provider":
            error_msg = (
                f"❌ CAPABILITY ERROR: Service providers cannot post buy requirements\n"
                f"Partner: {partner.legal_name}\n"
                f"Entity Class: {partner.entity_class}\n"
                f"Reason: Service providers (brokers, transporters, etc.) are not allowed to trade"
            )
            if raise_exception:
                raise CapabilityValidationError(error_msg, partner_id, "entity_class")
            return False, error_msg
        
        # Get capabilities
        capabilities = partner.capabilities if hasattr(partner, 'capabilities') else {}
        
        # Rule 2: Indian domestic buy
        if partner.country == "India" and delivery_country == "India":
            can_buy = capabilities.get("domestic_buy_india", False)
            if not can_buy:
                error_msg = (
                    f"❌ CAPABILITY ERROR: Partner lacks permission to buy domestically in India\n"
                    f"Partner: {partner.legal_name}\n"
                    f"Country: {partner.country}\n"
                    f"Required Capability: domestic_buy_india\n"
                    f"Current Status: {can_buy}\n"
                    f"Action Required: Verify GST Certificate + PAN Card to enable buying"
                )
                if raise_exception:
                    raise CapabilityValidationError(error_msg, partner_id, "domestic_buy_india")
                return False, error_msg
            return True, None
        
        # Rule 3: Foreign domestic buy (CRITICAL RULE)
        if partner.country != "India" and delivery_country == partner.country:
            can_buy = capabilities.get("domestic_buy_home_country", False)
            if not can_buy:
                error_msg = (
                    f"❌ CAPABILITY ERROR: Partner lacks permission to buy in home country\n"
                    f"Partner: {partner.legal_name}\n"
                    f"Country: {partner.country}\n"
                    f"Required Capability: domestic_buy_home_country\n"
                    f"Current Status: {can_buy}\n"
                    f"Action Required: Verify foreign tax registration documents"
                )
                if raise_exception:
                    raise CapabilityValidationError(error_msg, partner_id, "domestic_buy_home_country")
                return False, error_msg
            return True, None
        
        # Rule 4: Foreign entity trying to buy in India (BLOCKED)
        if partner.country != "India" and delivery_country == "India":
            error_msg = (
                f"❌ CAPABILITY ERROR: Foreign entities CANNOT buy domestically in India\n"
                f"Partner: {partner.legal_name}\n"
                f"Partner Country: {partner.country}\n"
                f"Delivery Location: {delivery_country}\n\n"
                f"⚠️ CRITICAL RULE VIOLATION:\n"
                f"Foreign entities can ONLY trade domestically in their home country.\n\n"
                f"To buy in India, you must:\n"
                f"1. Establish an Indian legal entity\n"
                f"2. Obtain Indian GST Certificate + PAN Card\n"
                f"3. Register as new Indian business partner\n\n"
                f"Alternative: Use import_allowed capability to buy FROM India (international trade)"
            )
            if raise_exception:
                raise CapabilityValidationError(error_msg, partner_id, "domestic_buy_india")
            return False, error_msg
        
        # Rule 5: Import (international buy)
        if partner.country != delivery_country:
            can_import = capabilities.get("import_allowed", False)
            if not can_import:
                error_msg = (
                    f"❌ CAPABILITY ERROR: Partner lacks import permission\n"
                    f"Partner: {partner.legal_name}\n"
                    f"Partner Country: {partner.country}\n"
                    f"Delivery Country: {delivery_country}\n"
                    f"Required Capability: import_allowed\n"
                    f"Current Status: {can_import}\n"
                    f"Action Required: Verify IEC + GST + PAN (India) OR Foreign Import License"
                )
                if raise_exception:
                    raise CapabilityValidationError(error_msg, partner_id, "import_allowed")
                return False, error_msg
            return True, None
        
        # Default: Allow
        return True, None
    
    async def validate_trade_parties(
        self,
        buyer_id: UUID,
        seller_id: UUID,
        buyer_delivery_country: str,
        seller_location_country: str,
        raise_exception: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate both buyer and seller capabilities for a trade.
        
        Args:
            buyer_id: Buyer partner UUID
            seller_id: Seller partner UUID
            buyer_delivery_country: Where buyer wants delivery
            seller_location_country: Where seller's goods are located
            raise_exception: If True, raise exception on failure
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Validate seller
        seller_valid, seller_error = await self.validate_sell_capability(
            partner_id=seller_id,
            location_country=seller_location_country,
            raise_exception=False
        )
        
        if not seller_valid:
            if raise_exception:
                raise CapabilityValidationError(seller_error, seller_id, "sell_capability")
            return False, seller_error
        
        # Validate buyer
        buyer_valid, buyer_error = await self.validate_buy_capability(
            partner_id=buyer_id,
            delivery_country=buyer_delivery_country,
            raise_exception=False
        )
        
        if not buyer_valid:
            if raise_exception:
                raise CapabilityValidationError(buyer_error, buyer_id, "buy_capability")
            return False, buyer_error
        
        return True, None
