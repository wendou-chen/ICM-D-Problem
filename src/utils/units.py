"""
Unit conversion and management utilities.
"""

from configs.constants import UnitRegistry

def tons_to_kg(tons: float) -> float:
    return tons * 1000.0

def kg_to_tons(kg: float) -> float:
    return kg / 1000.0

def years_to_months(years: float) -> float:
    return years * 12.0

def format_currency(amount: float) -> str:
    return f"${amount:,.2f}"

def format_mass(tons: float) -> str:
    if tons >= 1_000_000:
        return f"{tons/1_000_000:.2f}M tons"
    return f"{tons:,.0f} tons"
