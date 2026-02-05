import numpy as np
from typing import Dict, Any, Optional
from configs.constants import WaterDemand

def calculate_demand(
    population: int = WaterDemand.POPULATION,
    per_capita_usage_lpd: float = WaterDemand.W_L_PER_PERSON_DAY,
    recycling_rate: float = 0.0
) -> Dict[str, float]:
    """
    Calculate water demand metrics based on population and recycling parameters.
    
    Args:
        population: Number of people (default: {WaterDemand.POPULATION})
        per_capita_usage_lpd: Gross usage in Liters/person/day (default: {WaterDemand.W_L_PER_PERSON_DAY})
        recycling_rate: Fraction of water recycled (0.0 to 1.0)
        
    Returns:
        Dict with keys: net_per_capita_lpd, daily_tons, monthly_tons, annual_tons
    """
    # Net requirement is what is NOT recycled
    net_per_capita = per_capita_usage_lpd * (1.0 - recycling_rate)
    
    # Conversion: 1 Liter water ~= 1 kg = 0.001 Metric Tons
    daily_demand_tons = population * net_per_capita * 0.001
    
    # Monthly (30 days) and Annual (365 days)
    monthly_demand_tons = daily_demand_tons * 30.0
    annual_demand_tons = daily_demand_tons * 365.0
    
    return {
        'net_per_capita_lpd': net_per_capita,
        'daily_tons': daily_demand_tons,
        'monthly_tons': monthly_demand_tons,
        'annual_tons': annual_demand_tons
    }
