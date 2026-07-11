"""
Table generation for WSN Two-Layer Optimization paper.

Generates 3 tables from experiment data:
  Table 1: Comprehensive Performance Comparison
  Table 2: Algorithm Characteristics
  Table 3: Ablation Study Results
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.paths import table_path, experiment_data_dir
from src.data_parser import ExperimentDataParser

_parser = None

def _get_parser(data_root=None):
    global _parser
    if data_root is not None:
        return ExperimentDataParser(data_root)
    if _parser is None:
        _parser = ExperimentDataParser()
    return _parser


def table1_performance_comparison(data_root=None):
    """Table 1: Comprehensive Performance Comparison (300-node)."""
    print("Generating Table 1: Performance Comparison...")
    p = _get_parser(data_root)
    df = p.load_hnd_data(scale=300)
    
    summary = df.groupby('Protocol').agg({
        'HND': ['mean', 'std'],
        'EnergyEfficiency': ['mean', 'std'],
        'DeliveryRatio': ['mean', 'std'],
        'ConvergenceTime_ms': ['mean', 'std'],
        'JainsFairness': 'mean',
    }).round(3)
    
    # Flatten multi-level columns
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    
    # Add improvement column
    baseline_hnd = summary.loc['DeepSensor', 'HND_mean'] if 'DeepSensor' in summary.index else 0
    if baseline_hnd > 0:
        summary['HND_Improvement_pct'] = ((summary['HND_mean'] - baseline_hnd) / baseline_hnd * 100).round(1)
    else:
        summary['HND_Improvement_pct'] = 0.0
    
    # Reorder columns
    cols = ['HND_mean', 'HND_std', 'HND_Improvement_pct',
            'EnergyEfficiency_mean', 'EnergyEfficiency_std',
            'DeliveryRatio_mean', 'DeliveryRatio_std',
            'ConvergenceTime_ms_mean', 'ConvergenceTime_ms_std',
            'JainsFairness_mean']
    summary = summary[[c for c in cols if c in summary.columns]]
    
    # Rename for readability
    rename_map = {
        'HND_mean': 'HND (mean)',
        'HND_std': 'HND (std)',
        'HND_Improvement_pct': 'Improv. (%)',
        'EnergyEfficiency_mean': 'Energy Eff. (mean)',
        'EnergyEfficiency_std': 'Energy Eff. (std)',
        'DeliveryRatio_mean': 'Del. Ratio (mean)',
        'DeliveryRatio_std': 'Del. Ratio (std)',
        'ConvergenceTime_ms_mean': 'Conv. Time (ms)',
        'ConvergenceTime_ms_std': 'Conv. Time (std)',
        'JainsFairness_mean': 'Jain Fairness',
    }
    summary = summary.rename(columns=rename_map)
    
    summary.to_csv(table_path('table1_performance_comparison.csv'))
    print(f"  Done: table1_performance_comparison.csv")
    print(summary.to_string())
    return summary


def table2_algorithm_characteristics():
    """Table 2: Algorithm Characteristics Comparison."""
    print("Generating Table 2: Algorithm Characteristics...")
    
    data = {
        'Method': ['Centralized [3]', 'LEACH', 'HEED', 'PEGASIS', 'DeepSensor [13]', 'FL-Energy [11]', 'Ours'],
        'Distributed': ['No', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes'],
        'Convergence Guarantee': ['Yes (optimal)', 'No', 'No', 'No', 'No (empirical)', 'No (empirical)', 'Yes (O(1/√k))'],
        'Per-Node Complexity': ['O(N²)', 'O(N)', 'O(N)', 'O(N)', 'O(N·d)', 'O(N·d)', 'O(|N_i|+d)'],
        'Adaptation': ['No', 'No', 'Partial', 'No', 'Online (RL)', 'Online (FL)', 'Online (Feedback)'],
        'RAM (kB)': ['>10', '~3', '~4', '~3', '~12', '~8', '4.2'],
        'One-Hop Only': ['No', 'No', 'No', 'No', 'No', 'No', 'Yes'],
    }
    
    df = pd.DataFrame(data)
    df.to_csv(table_path('table2_algorithm_characteristics.csv'), index=False)
    print(f"  Done: table2_algorithm_characteristics.csv")
    print(df.to_string())
    return df


def table3_ablation_study(data_root=None):
    """Table 3: Ablation Study Results (300-node scenario)."""
    print("Generating Table 3: Ablation Study...")
    p = _get_parser(data_root)
    df = p.load_ablation_data()
    
    if not df.empty:
        df['HND_Δ (%)'] = ['-'] + [f'{(df.iloc[0]["HND_mean"] - df.iloc[i]["HND_mean"]) / df.iloc[0]["HND_mean"] * 100:.1f}' for i in range(1, len(df))]
    
    df.to_csv(table_path('table3_ablation_study.csv'), index=False)
    print(f"  Done: table3_ablation_study.csv")
    print(df.to_string())
    return df


def generate_all(data_root=None):
    """Generate all tables. Returns dict of {table_name: file_path}."""
    print("=" * 50)
    print("WSN Tables Generation")
    print("=" * 50)
    
    tab_paths = {}
    try:
        table1_performance_comparison(data_root)
        tab_paths['table1_performance_comparison'] = str(table_path('table1_performance_comparison.csv'))
        print()
        table2_algorithm_characteristics()
        tab_paths['table2_algorithm_characteristics'] = str(table_path('table2_algorithm_characteristics.csv'))
        print()
        table3_ablation_study(data_root)
        tab_paths['table3_ablation_study'] = str(table_path('table3_ablation_study.csv'))
        print(f"\nAll tables saved to: {table_path('')}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    return tab_paths


if __name__ == '__main__':
    generate_all()