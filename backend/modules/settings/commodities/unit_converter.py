"""
Universal Unit Converter

Handles automatic conversion between all units using the catalog.
NO manual conversion factors needed!

Uses EXACT conversions:
- CANDY = 355.6222 KG (784 pounds, factor 0.002812)
- All other units from catalog with precise Decimal arithmetic
"""

from decimal import Decimal
from typing import Dict, Any
from .unit_catalog import get_unit_info


class UnitConverter:
    """Automatic unit conversion system with multi-base support"""
    
    @staticmethod
    def convert_to_base(
        quantity: Decimal,
        from_unit: str,
        base_unit: str
    ) -> Decimal:
        """
        Convert any unit to its base unit (KG, METER, LITER, PIECE, SQ_METER).
        
        Args:
            quantity: Amount in from_unit (must be positive)
            from_unit: Source unit (BALE, MT, CANDY, etc.)
            base_unit: Target base unit (KG, METER, LITER, PIECE, SQ_METER)
        
        Returns:
            Quantity in base unit
        
        Raises:
            ValueError: If unit not found or quantity invalid
            
        Example:
            >>> UnitConverter.convert_to_base(Decimal("10"), "BALE", "KG")
            Decimal("1700.00")  # 10 × 170
            
            >>> UnitConverter.convert_to_base(Decimal("1"), "CANDY", "KG")
            Decimal("355.6222")  # EXACT
            
            >>> UnitConverter.convert_to_base(Decimal("5"), "MT", "KG")
            Decimal("5000.00")
        """
        # Validate quantity
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")
        
        # Get unit info
        unit_info = get_unit_info(from_unit)
        if not unit_info:
            raise ValueError(f"Unknown unit: {from_unit}")
        
        # Validate base unit compatibility
        catalog_base = unit_info["base_unit"]
        if catalog_base != base_unit:
            raise ValueError(
                f"Unit {from_unit} has base {catalog_base}, "
                f"but {base_unit} was requested"
            )
        
        # Convert
        conversion_factor = unit_info["conversion_factor"]
        return quantity * conversion_factor
    
    @staticmethod
    def convert_from_base(
        quantity_in_base: Decimal,
        base_unit: str,
        to_unit: str
    ) -> Decimal:
        """
        Convert base unit to target unit.
        
        Args:
            quantity_in_base: Amount in base unit
            base_unit: Base unit (KG, METER, LITER, PIECE, SQ_METER)
            to_unit: Target unit (CANDY, BALE, MT, etc.)
        
        Returns:
            Quantity in target unit
        
        Raises:
            ValueError: If unit not found or incompatible
            
        Example:
            >>> UnitConverter.convert_from_base(Decimal("355.6222"), "KG", "CANDY")
            Decimal("1")  # 355.6222 KG = 1 CANDY
            
            >>> UnitConverter.convert_from_base(Decimal("1000"), "KG", "QUINTAL")
            Decimal("10")  # 1000 KG = 10 QUINTAL
        """
        # Validate quantity
        if quantity_in_base <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity_in_base}")
        
        # Get unit info
        unit_info = get_unit_info(to_unit)
        if not unit_info:
            raise ValueError(f"Unknown unit: {to_unit}")
        
        # Validate base unit compatibility
        catalog_base = unit_info["base_unit"]
        if catalog_base != base_unit:
            raise ValueError(
                f"Unit {to_unit} has base {catalog_base}, "
                f"but {base_unit} was requested"
            )
        
        # Convert (divide by conversion factor)
        conversion_factor = unit_info["conversion_factor"]
        return quantity_in_base / conversion_factor
    
    @staticmethod
    def calculate_billing_amount(
        trade_quantity: Decimal,
        trade_unit: str,
        rate_per_unit: Decimal,
        rate_unit: str,
        base_unit: str
    ) -> Dict[str, Any]:
        """
        COMPLETE AUTO-CALCULATION for Trade Desk billing.
        
        This is the MAIN function Trade Desk will use for theoretical billing amounts.
        Returns complete breakdown with conversion factors and formula.
        
        NOTE: This is THEORETICAL only. Actual payment is handled in Accounts module.
        
        Args:
            trade_quantity: Quantity being traded (e.g., 600 BALES)
            trade_unit: Unit for trade quantity (e.g., "BALE")
            rate_per_unit: Price per rate unit (e.g., ₹50,000)
            rate_unit: Unit for rate (e.g., "CANDY")
            base_unit: Base unit for commodity (KG, METER, LITER, PIECE, SQ_METER)
        
        Returns:
            Complete breakdown dictionary with:
            - quantity_in_base_unit: Trade quantity converted to base
            - base_unit: Base unit used
            - rate_per_base_unit: Rate per base unit
            - billing_amount: Total theoretical billing amount
            - conversion_factors: Dict with conversion details
            - formula: Human-readable calculation formula
        
        Raises:
            ValueError: If units incompatible or invalid
            
        Example (Cotton: 600 BALES @ ₹50,000/CANDY):
            >>> result = UnitConverter.calculate_billing_amount(
            ...     trade_quantity=Decimal("600"),
            ...     trade_unit="BALE",
            ...     rate_per_unit=Decimal("50000"),
            ...     rate_unit="CANDY",
            ...     base_unit="KG"
            ... )
            >>> result["quantity_in_base_unit"]
            Decimal("102000")  # 600 × 170
            >>> result["billing_amount"]
            Decimal("14341200.00")  # 600×170×0.002812×50000
        """
        # Validate inputs
        if trade_quantity <= 0:
            raise ValueError(f"Trade quantity must be positive, got {trade_quantity}")
        if rate_per_unit <= 0:
            raise ValueError(f"Rate must be positive, got {rate_per_unit}")
        
        # Validate unit compatibility (both must have same base unit)
        trade_info = get_unit_info(trade_unit)
        rate_info = get_unit_info(rate_unit)
        
        if not trade_info:
            raise ValueError(f"Unknown trade unit: {trade_unit}")
        if not rate_info:
            raise ValueError(f"Unknown rate unit: {rate_unit}")
        
        if trade_info["base_unit"] != base_unit:
            raise ValueError(
                f"Trade unit {trade_unit} has base {trade_info['base_unit']}, "
                f"incompatible with base units {base_unit}"
            )
        
        if rate_info["base_unit"] != base_unit:
            raise ValueError(
                f"Rate unit {rate_unit} has base {rate_info['base_unit']}, "
                f"incompatible with base units {base_unit}"
            )
        
        # STEP 1: Convert trade quantity to base unit
        quantity_in_base = UnitConverter.convert_to_base(
            trade_quantity,
            trade_unit,
            base_unit
        )
        
        # STEP 2: Convert rate to base unit
        # rate_per_unit is price per rate_unit
        # We need price per base_unit
        # Example: ₹50,000/CANDY → ₹50,000/355.6222 KG = ₹140.61/KG
        rate_unit_factor = rate_info["conversion_factor"]
        rate_per_base = rate_per_unit / rate_unit_factor
        
        # STEP 3: Calculate billing amount
        # billing_amount = quantity_in_base × rate_per_base
        billing_amount = quantity_in_base * rate_per_base
        
        # Build conversion factors string
        trade_factor_str = f"1 {trade_unit} = {trade_info['conversion_factor']} {base_unit}"
        rate_factor_str = f"1 {rate_unit} = {rate_info['conversion_factor']} {base_unit}"
        
        # Build calculation formula
        # Example: "600 BALES × 170 KG/BALE × 0.002812 CANDY/KG × ₹50,000/CANDY = ₹14,341,200"
        candy_per_kg = Decimal("1") / rate_unit_factor if rate_unit_factor != Decimal("1") else Decimal("1")
        
        formula = (
            f"{trade_quantity} {trade_unit} × "
            f"{trade_info['conversion_factor']} {base_unit}/{trade_unit} × "
            f"{candy_per_kg:.6f} {rate_unit}/{base_unit} × "
            f"₹{rate_per_unit:,} /{rate_unit} = "
            f"₹{billing_amount:,.0f}"
        )
        
        return {
            "quantity_in_base_unit": quantity_in_base,
            "base_unit": base_unit,
            "rate_per_base_unit": rate_per_base,
            "billing_amount": billing_amount,
            "conversion_factors": {
                "trade_unit_to_base": trade_factor_str,
                "rate_unit_to_base": rate_factor_str
            },
            "formula": formula
        }
    
    @staticmethod
    def validate_units_compatibility(
        trade_unit: str,
        rate_unit: str,
        base_unit: str
    ) -> bool:
        """
        Validate that trade_unit and rate_unit are compatible with base_unit.
        
        Args:
            trade_unit: Trade quantity unit
            rate_unit: Rate pricing unit
            base_unit: Expected base unit
        
        Returns:
            True if compatible
        
        Raises:
            ValueError: If units are incompatible
            
        Example:
            >>> UnitConverter.validate_units_compatibility("BALE", "CANDY", "KG")
            True  # Both BALE and CANDY have KG base
            
            >>> UnitConverter.validate_units_compatibility("BALE", "METER", "KG")
            ValueError: incompatible base units
        """
        trade_info = get_unit_info(trade_unit)
        rate_info = get_unit_info(rate_unit)
        
        if not trade_info:
            raise ValueError(f"Unknown unit: {trade_unit}")
        if not rate_info:
            raise ValueError(f"Unknown unit: {rate_unit}")
        
        if trade_info["base_unit"] != base_unit:
            raise ValueError(
                f"Trade unit {trade_unit} has incompatible base units: "
                f"{trade_info['base_unit']} vs {base_unit}"
            )
        
        if rate_info["base_unit"] != base_unit:
            raise ValueError(
                f"Rate unit {rate_unit} has incompatible base units: "
                f"{rate_info['base_unit']} vs {base_unit}"
            )
        
        return True
