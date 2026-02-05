import matplotlib.pyplot as plt
import seaborn as sns
import os
import pandas as pd
from typing import Any
from src.utils.plot_style import apply_style

def plot_demand_sensitivity(df: pd.DataFrame, output_path: str):
    """
    Plot Annual Water Transport Demand vs Recycling Rate.
    df columns: recycling_rate, annual_tons
    """
    apply_style()
    plt.figure(figsize=(10, 6))
    # Create the line plot
    sns.lineplot(data=df, x='recycling_rate', y='annual_tons', marker='o', linewidth=2.5, label='Annual Demand')
    
    # Add ISS reference line
    plt.axvline(x=0.98, color='green', linestyle='--', label='ISS Standard (98%)')
    
    plt.xlabel('Water Recycling Rate (eta)')
    plt.ylabel('Annual Transport Requirement (Tons)')
    plt.title('Impact of Recycling on Lunar Water Logistics (Step 1)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()

def plot_capacity_vs_demand(df: pd.DataFrame, elevator_capacity_ton_year: float, output_path: str):
    """
    Plot Annual Demand vs Elevator Capacity Limit.
    df columns: recycling_rate, annual_tons
    """
    apply_style()
    plt.figure(figsize=(10, 6))
    
    # Bar plot for demand
    sns.barplot(data=df, x='recycling_rate', y='annual_tons', palette='Blues_d')
    
    # Horizontal line for Elevator Capacity
    plt.axhline(y=elevator_capacity_ton_year, color='red', linestyle='--', linewidth=2, 
                label=f'Max Elevator Capacity ({elevator_capacity_ton_year:,.0f} t/yr)')
    
    plt.xlabel('Recycling Rate (eta)')
    plt.ylabel('Annual Tons')
    plt.title('Water Demand vs. Total Elevator Capacity')
    plt.legend()
    plt.grid(True, axis='y', alpha=0.3)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()

def plot_reliability_curve(df: pd.DataFrame, output_path: str):
    """
    Plot Probability of No Stockout vs Initial Inventory Buffer.
    df columns: buffer_months, p_success
    """
    apply_style()
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x='buffer_months', y='p_success', palette='viridis')
    
    # Threshold line
    plt.axhline(y=0.95, color='red', linestyle='--', label='95% Reliability Target')
    
    plt.xlabel('Initial Inventory Buffer (Months)')
    plt.ylabel('Probability of Continuous Service (1 Year)')
    plt.title('Service Reliability vs Inventory Strategy (Severe Scenario)')
    plt.ylim(0, 1.05)
    plt.legend()
    plt.grid(True, axis='y', alpha=0.3)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()

def plot_inventory_traces(traces: list, output_path: str):
    """
    Plot random inventory trajectories.
    traces: list of lists (daily inventory levels)
    """
    apply_style()
    plt.figure(figsize=(12, 6))
    for i, trace in enumerate(traces):
        plt.plot(trace, alpha=0.7, label=f'Sim {i+1}')
        
    plt.axhline(y=0, color='red', linestyle='-', linewidth=1, label='Stockout Limit')
    
    plt.xlabel('Day')
    plt.ylabel('Water Inventory (Tons)')
    plt.title('Monte Carlo Simulation of Water Inventory (Severe Scenario)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()
