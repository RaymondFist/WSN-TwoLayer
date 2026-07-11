"""
Data Parser for WSN experiment output.

Reads CSV files produced by wsn-experiment and transforms them
into structured DataFrames for analysis and visualization.
"""
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional

from src.paths import experiment_data_dir


class ExperimentDataParser:
    """Parses raw experiment CSV output into analysis-ready DataFrames."""
    
    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = data_root or experiment_data_dir()
        self._cache = {}
    
    def load_hnd_data(self, scale: Optional[int] = None) -> pd.DataFrame:
        """
        Load HND (Heterogeneous Node Death) data.
        Returns DataFrame with columns: Protocol, Scale, Run, HND, EnergyEfficiency, DeliveryRatio, ConvergenceTime_ms, JainsFairness
        """
        data_dir = self.data_root / f'scale_{scale}' if scale else self.data_root
        
        all_dfs = []
        if scale:
            paths = [data_dir / 'hnd_by_scale.csv']
        else:
            # Aggregate across all scales
            paths = sorted(data_dir.glob('scale_*/hnd_by_scale.csv'))
        
        for p in paths:
            if p.exists():
                df = pd.read_csv(p)
                all_dfs.append(df)
        
        if not all_dfs:
            raise FileNotFoundError(f"No HND data found at {data_dir}")
        
        return pd.concat(all_dfs, ignore_index=True)
    
    def load_energy_timeseries(self, scale: Optional[int] = None) -> pd.DataFrame:
        """
        Load energy consumption time series.
        Returns DataFrame with columns: Protocol, Round, NodeID, Energy_mW, Normalized_Energy
        """
        data_dir = self.data_root / f'scale_{scale}' if scale else self.data_root
        
        all_dfs = []
        if scale:
            paths = [data_dir / 'energy_timeseries.csv']
        else:
            paths = sorted(data_dir.glob('scale_*/energy_timeseries.csv'))
        
        for p in paths:
            if p.exists():
                df = pd.read_csv(p)
                all_dfs.append(df)
        
        if not all_dfs:
            raise FileNotFoundError(f"No energy time series data found at {data_dir}")
        
        return pd.concat(all_dfs, ignore_index=True)
    
    def load_fairness_data(self, scale: Optional[int] = None) -> pd.DataFrame:
        """
        Load Jain's fairness index over time.
        Returns DataFrame with columns: Protocol, Round, Jains_Index
        """
        data_dir = self.data_root / f'scale_{scale}' if scale else self.data_root
        
        all_dfs = []
        if scale:
            paths = [data_dir / 'jain_fairness.csv']
        else:
            paths = sorted(data_dir.glob('scale_*/jain_fairness.csv'))
        
        for p in paths:
            if p.exists():
                df = pd.read_csv(p)
                all_dfs.append(df)
        
        if not all_dfs:
            raise FileNotFoundError(f"No fairness data found at {data_dir}")
        
        return pd.concat(all_dfs, ignore_index=True)
    
    def load_ablation_data(self) -> pd.DataFrame:
        """
        Load ablation study results.
        Returns DataFrame with columns: Variant, HND_mean, HND_std, DR_mean, DR_std, Conv_mean, Conv_std
        """
        data_dir = self.data_root
        
        all_dfs = []
        paths = sorted(data_dir.glob('**/ablation_study.csv'))
        
        for p in paths:
            if p.exists():
                df = pd.read_csv(p)
                all_dfs.append(df)
        
        if not all_dfs:
            raise FileNotFoundError(f"No ablation data found at {data_dir}")
        
        return pd.concat(all_dfs, ignore_index=True)
    
    def load_convergence_data(self) -> pd.DataFrame:
        """
        Load convergence data (consensus error, gradient norm).
        Returns DataFrame with columns: Protocol, Scale, Round, ConsensusError, GradientNorm, Normalized_Energy
        """
        data_dir = self.data_root
        
        all_dfs = []
        paths = sorted(data_dir.glob('**/convergence_data.csv'))
        
        for p in paths:
            if p.exists():
                df = pd.read_csv(p)
                # Extract scale from path (e.g., scale_300/convergence_data.csv)
                scale_dir = p.parent.name
                if scale_dir.startswith('scale_'):
                    df['Scale'] = int(scale_dir.split('_')[1])
                all_dfs.append(df)
        
        if not all_dfs:
            raise FileNotFoundError(f"No convergence data found at {data_dir}")
        
        return pd.concat(all_dfs, ignore_index=True)
    
    def load_metadata(self) -> dict:
        """Load experiment run metadata."""
        paths = list(self.data_root.glob('**/run_metadata.json'))
        if paths:
            with open(paths[0], 'r') as f:
                return json.load(f)
        return {}
    
    def get_protocol_summary(self, scale: int = 300) -> pd.DataFrame:
        """
        Get summary statistics for all protocols at a given scale.
        Returns DataFrame with mean and std for key metrics.
        """
        df = self.load_hnd_data(scale)
        
        summary = df.groupby('Protocol').agg({
            'HND': ['mean', 'std'],
            'EnergyEfficiency': ['mean', 'std'],
            'DeliveryRatio': ['mean', 'std'],
            'ConvergenceTime_ms': ['mean', 'std'],
            'JainsFairness': ['mean', 'std'],
        }).round(4)
        
        return summary

# Convenience function
def load_all_data(data_root: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """Load all experiment data at once. Gracefully skips missing optional files."""
    parser = ExperimentDataParser(data_root)
    result = {}
    for key, loader in [
        ('hnd', parser.load_hnd_data),
        ('energy', parser.load_energy_timeseries),
        ('fairness', parser.load_fairness_data),
    ]:
        try:
            result[key] = loader()
        except FileNotFoundError:
            result[key] = pd.DataFrame()
    try:
        result['ablation'] = parser.load_ablation_data()
    except FileNotFoundError:
        result['ablation'] = pd.DataFrame()
    try:
        result['convergence'] = parser.load_convergence_data()
    except FileNotFoundError:
        result['convergence'] = pd.DataFrame()
    try:
        result['metadata'] = parser.load_metadata()
    except Exception:
        result['metadata'] = {}
    return result