"""
Currency Converter Integration for Commodities

Adds real-time currency conversion capabilities to commodity pricing.
"""

from typing import Dict, List, Optional
from decimal import Decimal
from backend.core.global_services.currency_converter import CurrencyConversionService, ExchangeRate


class CommodityPricingService:
    """
    Service for multi-currency commodity pricing with real-time conversion.
    
    Integrates CurrencyConversionService with commodity module for:
    - Converting prices between supported currencies
    - Batch price conversion for reporting
    - Real-time pricing in buyer's preferred currency
    """
    
    def __init__(self):
        self.currency_converter = CurrencyConversionService()
    
    async def convert_commodity_price(
        self,
        price: Decimal,
        from_currency: str,
        to_currency: str,
        use_cache: bool = True
    ) -> Dict:
        """
        Convert commodity price from one currency to another.
        
        Args:
            price: Price amount in base currency
            from_currency: Source currency (e.g., USD)
            to_currency: Target currency (e.g., INR)
            use_cache: Whether to use cached exchange rates
        
        Returns:
            Dict with converted price, rate, and metadata
        
        Example:
            >>> service = CommodityPricingService()
            >>> result = await service.convert_commodity_price(
            ...     price=Decimal("100"),
            ...     from_currency="USD",
            ...     to_currency="INR"
            ... )
            >>> print(result)
            {
                "original_price": 100.00,
                "original_currency": "USD",
                "converted_price": 8312.00,
                "converted_currency": "INR",
                "exchange_rate": 83.12,
                "timestamp": "2024-12-04T10:00:00",
                "source": "exchangerate-api.com"
            }
        """
        # Get exchange rate
        rate_info = await self.currency_converter.get_rate(
            base_currency=from_currency,
            target_currency=to_currency,
            use_cache=use_cache
        )
        
        # Calculate converted price
        converted_price = price * rate_info.rate
        
        return {
            "original_price": float(price),
            "original_currency": from_currency.upper(),
            "converted_price": float(converted_price.quantize(Decimal("0.01"))),
            "converted_currency": to_currency.upper(),
            "exchange_rate": float(rate_info.rate),
            "timestamp": rate_info.timestamp.isoformat(),
            "source": rate_info.source
        }
    
    async def get_price_in_multiple_currencies(
        self,
        price: Decimal,
        base_currency: str,
        target_currencies: List[str]
    ) -> Dict:
        """
        Convert a single price to multiple currencies.
        
        Useful for international commodity listings showing prices in:
        - USD (global standard)
        - INR (domestic Indian market)
        - EUR (European buyers)
        - CNY (Chinese buyers)
        
        Args:
            price: Base price amount
            base_currency: Currency of base price
            target_currencies: List of currencies to convert to
        
        Returns:
            Dict mapping currency codes to converted prices
        
        Example:
            >>> service = CommodityPricingService()
            >>> result = await service.get_price_in_multiple_currencies(
            ...     price=Decimal("1000"),
            ...     base_currency="USD",
            ...     target_currencies=["INR", "EUR", "CNY"]
            ... )
            >>> print(result)
            {
                "base": {"amount": 1000.00, "currency": "USD"},
                "conversions": {
                    "INR": {"amount": 83120.00, "rate": 83.12},
                    "EUR": {"amount": 920.00, "rate": 0.92},
                    "CNY": {"amount": 7240.00, "rate": 7.24}
                },
                "timestamp": "2024-12-04T10:00:00"
            }
        """
        conversions = {}
        timestamp = None
        
        for target_currency in target_currencies:
            conversion = await self.convert_commodity_price(
                price=price,
                from_currency=base_currency,
                to_currency=target_currency
            )
            
            conversions[target_currency.upper()] = {
                "amount": conversion["converted_price"],
                "rate": conversion["exchange_rate"]
            }
            
            if not timestamp:
                timestamp = conversion["timestamp"]
        
        return {
            "base": {
                "amount": float(price),
                "currency": base_currency.upper()
            },
            "conversions": conversions,
            "timestamp": timestamp
        }
    
    async def calculate_cents_per_pound(
        self,
        price_per_kg: Decimal,
        currency: str = "USD"
    ) -> Decimal:
        """
        Convert price per KG to CENTS_PER_POUND (cotton industry standard).
        
        Formula:
        1. Convert KG to POUND: 1 KG = 2.20462 LB
        2. Divide by pounds to get price per pound
        3. Multiply by 100 to get cents
        
        Args:
            price_per_kg: Price in currency per kilogram
            currency: Currency code (should be USD for standard cotton pricing)
        
        Returns:
            Price in cents per pound
        
        Example:
            >>> service = CommodityPricingService()
            >>> cents_per_lb = await service.calculate_cents_per_pound(
            ...     price_per_kg=Decimal("2.00"),  # $2 per kg
            ...     currency="USD"
            ... )
            >>> print(cents_per_lb)
            90.72  # cents per pound
        """
        KG_TO_POUND = Decimal("2.20462")
        
        # Price per pound in dollars
        price_per_pound = price_per_kg / KG_TO_POUND
        
        # Convert to cents
        cents_per_pound = price_per_pound * 100
        
        return cents_per_pound.quantize(Decimal("0.01"))
    
    async def calculate_kg_from_cents_per_pound(
        self,
        cents_per_pound: Decimal,
        currency: str = "USD"
    ) -> Decimal:
        """
        Convert CENTS_PER_POUND back to price per KG.
        
        Reverse of calculate_cents_per_pound.
        
        Args:
            cents_per_pound: Price in cents per pound
            currency: Currency code
        
        Returns:
            Price per kilogram in currency
        
        Example:
            >>> service = CommodityPricingService()
            >>> price_per_kg = await service.calculate_kg_from_cents_per_pound(
            ...     cents_per_pound=Decimal("90.72")
            ... )
            >>> print(price_per_kg)
            2.00  # USD per kg
        """
        KG_TO_POUND = Decimal("2.20462")
        
        # Convert cents to dollars
        dollars_per_pound = cents_per_pound / 100
        
        # Convert pounds to kg
        price_per_kg = dollars_per_pound * KG_TO_POUND
        
        return price_per_kg.quantize(Decimal("0.01"))
    
    def get_supported_currencies(self) -> List[str]:
        """
        Get list of all supported currencies.
        
        Returns:
            List of currency codes
        """
        return self.currency_converter.SUPPORTED_CURRENCIES


# Export for use in commodity service
__all__ = ["CommodityPricingService"]
