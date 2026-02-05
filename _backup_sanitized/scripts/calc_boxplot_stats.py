import pandas as pd
import numpy as np
import sys

def calculate_stats(file_path):
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return

    results = []
    
    for col in df.columns:
        series = df[col].dropna()
        if len(series) == 0:
            continue
            
        q1 = series.quantile(0.25)
        median = series.quantile(0.50)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        
        # Theoretical whisker bounds
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Actual min/max
        min_val = series.min()
        max_val = series.max()
        
        results.append({
            "Scenario": col,
            "Min": min_val,
            "Q1": q1,
            "Median": median,
            "Q3": q3,
            "Max": max_val,
            "Lower_Whisker_Limit": lower_bound,
            "Upper_Whisker_Limit": upper_bound
        })
        
    print(f"{'Scenario':<30} | {'Min':<10} | {'Q1':<10} | {'Median':<10} | {'Q3':<10} | {'Max':<10} | {'Low_W_Lim':<10} | {'Up_W_Lim':<10}")
    print("-" * 125)
    for row in results:
        print(f"{row['Scenario']:<30} | {row['Min']:.4f}     | {row['Q1']:.4f}     | {row['Median']:.4f}     | {row['Q3']:.4f}     | {row['Max']:.4f}     | {row['Lower_Whisker_Limit']:.4f}     | {row['Upper_Whisker_Limit']:.4f}")

if __name__ == "__main__":
    calculate_stats("outputs/q2/data/boxplot_raw_data.csv")
