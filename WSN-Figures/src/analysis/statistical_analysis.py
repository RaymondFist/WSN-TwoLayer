"""
Statistical analysis for WSN experiment results.

Computes:
- p-values (Welch's t-test)
- Cohen's d effect sizes
- 95% confidence intervals
- Mean and standard deviation
- Super-additive gain analysis
- Convergence rate estimation
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Tuple, Optional


class StatisticalAnalyzer:
    """Statistical analysis of WSN experiment results."""
    
    def __init__(self, data: Dict[str, pd.DataFrame]):
        self.data = data
        self.hnd = data.get('hnd', pd.DataFrame())
        self.energy = data.get('energy', pd.DataFrame())
        self.fairness = data.get('fairness', pd.DataFrame())
        self.ablation = data.get('ablation', pd.DataFrame())
        self.convergence = data.get('convergence', pd.DataFrame())
    
    def t_test(self, group_a: pd.Series, group_b: pd.Series) -> Tuple[float, float]:
        """
        Welch's t-test for independent samples with unequal variance.
        Returns (t_statistic, p_value).
        """
        if len(group_a) < 2 or len(group_b) < 2:
            return 0.0, 1.0
        
        t_stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)
        return t_stat, p_value
    
    def cohens_d(self, group_a: pd.Series, group_b: pd.Series) -> float:
        """Cohen's d effect size with pooled standard deviation."""
        n1, n2 = len(group_a), len(group_b)
        if n1 < 2 or n2 < 2:
            return 0.0
        
        pooled_std = np.sqrt(((n1 - 1) * group_a.std()**2 + (n2 - 1) * group_b.std()**2) / (n1 + n2 - 2))
        
        if pooled_std < 1e-10:
            return 0.0
        
        return (group_a.mean() - group_b.mean()) / pooled_std
    
    def confidence_interval(self, data: pd.Series, confidence: float = 0.95) -> Tuple[float, float]:
        """Compute confidence interval for the mean."""
        if len(data) < 2:
            return data.mean(), data.mean()
        
        mean = data.mean()
        sem = stats.sem(data)
        ci = sem * stats.t.ppf((1 + confidence) / 2, len(data) - 1)
        return mean - ci, mean + ci
    
    def compare_protocols(self, our_protocol: str = 'Ours',
                          baseline_protocol: str = 'DeepSensor',
                          metric: str = 'HND',
                          scale: Optional[int] = None) -> Dict:
        """
        Comprehensive comparison between two protocols.
        Returns dict with improvement_pct, p_value, cohens_d, confidence_intervals.
        """
        df = self.hnd
        if scale is not None:
            df = df[df['Scale'] == scale]
        
        ours = df[df['Protocol'] == our_protocol][metric]
        baseline = df[df['Protocol'] == baseline_protocol][metric]
        
        if len(ours) == 0 or len(baseline) == 0:
            return {'improvement_pct': 0, 'p_value': 1.0, 'cohens_d': 0.0}
        
        improvement = (ours.mean() - baseline.mean()) / baseline.mean() * 100
        _, p_val = self.t_test(ours, baseline)
        d = self.cohens_d(ours, baseline)
        ci_ours = self.confidence_interval(ours)
        ci_baseline = self.confidence_interval(baseline)
        
        return {
            'our_mean': ours.mean(),
            'our_std': ours.std(),
            'our_ci': ci_ours,
            'baseline_mean': baseline.mean(),
            'baseline_std': baseline.std(),
            'baseline_ci': ci_baseline,
            'improvement_pct': improvement,
            'p_value': p_val,
            'cohens_d': d,
            'significant': p_val < 0.05,
        }
    
    def compute_super_additive_gain(self) -> float:
        """
        Compute super-additive gain: the excess benefit of the full framework
        over the sum of individual component gains.
        
        Super-additivity means: gain(L2 + adaptive) > gain(L2) + gain(adaptive)
        where gain(X) = HND(with X) - HND(without X).
        
        Uses the "w/o both" variant as baseline when available, otherwise
        falls back to the worst single ablation as a conservative lower bound.
        """
        if self.ablation.empty:
            return 0.0
        
        full = self.ablation[self.ablation['Variant'] == 'Full framework']
        w_o_l2 = self.ablation[self.ablation['Variant'] == 'w/o Layer 2']
        fixed_w = self.ablation[self.ablation['Variant'] == 'Fixed weights']
        w_o_both = self.ablation[self.ablation['Variant'] == 'w/o both']
        
        if full.empty or w_o_l2.empty or fixed_w.empty:
            return 0.0
        
        full_hnd = full['HND_mean'].values[0]
        w_o_l2_hnd = w_o_l2['HND_mean'].values[0]
        fixed_w_hnd = fixed_w['HND_mean'].values[0]
        
        # Individual component gains
        l2_gain = full_hnd - w_o_l2_hnd    # Gain from adding Layer 2
        fw_gain = full_hnd - fixed_w_hnd    # Gain from adding adaptive weights
        sum_gains = l2_gain + fw_gain
        
        if not w_o_both.empty:
            # Direct measurement: both components disabled
            baseline_hnd = w_o_both['HND_mean'].values[0]
            total_gain = full_hnd - baseline_hnd
        else:
            # Conservative fallback: worst single ablation
            baseline_hnd = min(w_o_l2_hnd, fixed_w_hnd)
            total_gain = full_hnd - baseline_hnd
        
        if sum_gains < 1e-10:
            return 0.0
        
        # Positive = super-additive (synergy), Negative = sub-additive
        return (total_gain - sum_gains) / sum_gains * 100
    
    def compute_convergence_rate(self, scale: int = 300) -> float:
        """
        Estimate convergence rate from gradient norm data at a given scale.
        Fits O(1/k^r) to the gradient norm decay during the
        convergence phase (first 25% of iterations) to avoid
        steady-state plateau skewing the regression.
        The O(1/√k) guarantee applies to the optimization gradient norm.
        Returns estimated rate r (should be ≈ 0.5 for O(1/√k)).
        """
        if not self.convergence.empty:
            ours = self.convergence[self.convergence['Protocol'] == 'Ours']
            if 'Scale' in ours.columns:
                ours = ours[ours['Scale'] == scale]
            if ours.empty:
                return 0.0
            # Use convergence phase only (first 25% of rounds)
            # to avoid steady-state plateau skewing log-log regression
            max_round = ours['Round'].max()
            convergence_phase = ours[ours['Round'] <= max_round // 4]
            later = convergence_phase[convergence_phase['GradientNorm'] > 1e-10]
            if len(later) < 10:
                return 0.0
            x = np.log(later['Round'].values + 1)
            y = np.log(later['GradientNorm'].values)
        elif not self.energy.empty:
            ours = self.energy[self.energy['Protocol'] == 'Ours']
            if ours.empty:
                return 0.0
            later = ours[ours['Round'] >= ours['Round'].max() // 2]
            if len(later) < 10:
                return 0.0
            x = np.log(later['Round'].values + 1)
            y = np.log(later['Normalized_Energy'].values + 1e-10)
        else:
            return 0.0
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        return -slope  # Rate exponent
    
    def full_report(self, scale: int = 300) -> str:
        """Generate a complete statistical report."""
        lines = []
        lines.append("=" * 60)
        lines.append("WSN Two-Layer Experiment - Statistical Report")
        lines.append("=" * 60)
        
        # Protocol comparison
        lines.append(f"\n--- Protocol Comparison ({scale} nodes) ---")
        baselines = ['LEACH', 'HEED', 'PEGASIS', 'DeepSensor', 'FL-Energy']
        
        for baseline in baselines:
            comp = self.compare_protocols('Ours', baseline, scale=scale)
            sig = "***" if comp['p_value'] < 0.001 else ("**" if comp['p_value'] < 0.01 else ("*" if comp['p_value'] < 0.05 else "ns"))
            lines.append(f"  Ours vs {baseline}:")
            lines.append(f"    Improvement: {comp['improvement_pct']:.1f}%")
            lines.append(f"    p-value: {comp['p_value']:.4f} {sig}")
            lines.append(f"    Cohen's d: {comp['cohens_d']:.2f}")
        
        # Ablation analysis
        lines.append(f"\n--- Ablation Study ---")
        super_add = self.compute_super_additive_gain()
        lines.append(f"  Super-additive gain: {super_add:.1f}%")
        
        # Convergence rate
        lines.append(f"\n--- Convergence Analysis ---")
        rate = self.compute_convergence_rate()
        lines.append(f"  Estimated convergence rate: {rate:.3f} (theoretical: O(1/√k) ≈ 0.5)")
        lines.append(f"  Rate match: {'YES' if 0.3 < rate < 0.7 else 'DEVIATES'}")
        
        lines.append(f"\n{'=' * 60}")
        return '\n'.join(lines)