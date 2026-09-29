"""
Figure generation for WSN Two-Layer Optimization.

Generates Figs. 2-7 from the experiment data.
Output: 300 DPI, grayscale-compatible, single- and double-column widths.

Figures:
  Fig 2: Network lifetime (HND) comparison across scales
  Fig 3: Energy consumption per round
  Fig 4: Load balancing (Jain's fairness) over time
  Fig 5: Packet delivery ratio vs network density
  Fig 6: Convergence behaviour (consensus error, gradient norm, normalized energy)
  Fig 7: Multi-scale HND: Ours against the DRL-based baseline
"""
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.paths import figure_path, experiment_data_dir
from src.data_parser import ExperimentDataParser

# Global style settings
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
})

# Grayscale-compatible color palette
COLORS = {
    'LEACH': '#333333',
    'HEED': '#666666',
    'PEGASIS': '#999999',
    'DeepSensor': '#BBBBBB',
    'FL-Energy': '#555555',
    'Ours': '#000000',
}
MARKERS = {
    'LEACH': 's',
    'HEED': '^',
    'PEGASIS': 'D',
    'DeepSensor': 'o',
    'FL-Energy': 'v',
    'Ours': '*',
}
LINESTYLES = {
    'LEACH': ':',
    'HEED': '--',
    'PEGASIS': '-.',
    'DeepSensor': (0, (3, 2, 1, 2)),
    'FL-Energy': (0, (5, 3)),
    'Ours': '-',
}
PROTOCOL_ORDER = ['LEACH', 'HEED', 'PEGASIS', 'DeepSensor', 'FL-Energy', 'Ours']
# Legend label for the DRL baseline, which is reference [10] in the paper
LABELS = {'DeepSensor': 'DRL-based[10]'}

_parser = None

def _get_parser(data_root=None):
    global _parser
    if data_root is not None:
        return ExperimentDataParser(data_root)
    if _parser is None:
        _parser = ExperimentDataParser()
    return _parser


def fig2_network_lifetime(data_root=None):
    """Fig 2: Network lifetime (HND) comparison across network scales."""
    print("Generating Fig 2: Network lifetime...")
    p = _get_parser(data_root)
    df = p.load_hnd_data()
    
    scales = sorted(df['Scale'].unique())
    protocols = [p for p in PROTOCOL_ORDER if p in df['Protocol'].unique()]
    
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    
    x = np.arange(len(scales))
    width = 0.13
    multiplier = 0
    
    for protocol in protocols:
        means = []
        stds = []
        for scale in scales:
            subset = df[(df['Protocol'] == protocol) & (df['Scale'] == scale)]
            means.append(subset['HND'].mean())
            stds.append(subset['HND'].std())
        
        offset = width * multiplier
        bars = ax.bar(x + offset, means, width, label=LABELS.get(protocol, protocol),
                      color=COLORS.get(protocol, '#888888'),
                      edgecolor='black', linewidth=0.3,
                      yerr=stds, capsize=2, error_kw={'linewidth': 0.5})
        multiplier += 1
    
    ax.set_xlabel('Network Scale (nodes)')
    ax.set_ylabel('HND (rounds)')
    ax.set_xticks(x + width * 2.5)
    ax.set_xticklabels(scales)
    ax.legend(loc='upper left', ncol=2, frameon=True, fancybox=False,
              edgecolor='black', fontsize=7)
    ax.grid(axis='y', alpha=0.3, linestyle=':')
    ax.set_ylim(bottom=0)
    
    # Add improvement annotation
    ours_300 = df[(df['Protocol'] == 'Ours') & (df['Scale'] == 300)]['HND'].mean()
    baseline_300 = df[(df['Protocol'] == 'DeepSensor') & (df['Scale'] == 300)]['HND'].mean()
    if not pd.isna(ours_300) and not pd.isna(baseline_300) and baseline_300 > 0:
        improvement = (ours_300 - baseline_300) / baseline_300 * 100
        idx_300 = scales.index(300) if 300 in scales else 2
        ax.annotate(f'+{improvement:.1f}%',
                    xy=(x[idx_300] + width * 5.5, ours_300),
                    xytext=(0, 8), textcoords='offset points',
                    fontsize=7, ha='center', fontweight='bold')
    
    plt.tight_layout()
    fig.savefig(figure_path('fig2_network_lifetime.png'))
    plt.close()
    print("  Done: fig2_network_lifetime.png")


def fig3_energy_consumption(data_root=None):
    """Fig 3: Energy consumption per round."""
    print("Generating Fig 3: Energy consumption...")
    p = _get_parser(data_root)
    df = p.load_energy_timeseries()
    
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    
    for protocol in PROTOCOL_ORDER:
        if protocol not in df['Protocol'].unique():
            continue
        subset = df[df['Protocol'] == protocol]
        # Aggregate: mean energy per round across all nodes
        energy_by_round = subset.groupby('Round')['Normalized_Energy'].mean()
        
        # Downsample for plotting
        if len(energy_by_round) > 200:
            step = max(1, len(energy_by_round) // 200)
            energy_by_round = energy_by_round.iloc[::step]
        
        ax.plot(energy_by_round.index, energy_by_round.values,
                color=COLORS.get(protocol, '#888888'),
                linestyle=LINESTYLES.get(protocol, '-'),
                linewidth=1.0 if protocol == 'Ours' else 0.7,
                label=LABELS.get(protocol, protocol))
    
    ax.set_xlabel('Simulation Round')
    ax.set_ylabel('Normalized Energy')
    ax.legend(loc='upper right', ncol=2, frameon=True, fancybox=False,
              edgecolor='black', fontsize=7)
    ax.grid(alpha=0.3, linestyle=':')
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    fig.savefig(figure_path('fig3_energy_consumption.png'))
    plt.close()
    print("  Done: fig3_energy_consumption.png")


def fig4_load_balancing(data_root=None):
    """Fig 4: Load balancing (Jain's fairness index) over time."""
    print("Generating Fig 4: Load balancing...")
    p = _get_parser(data_root)
    df = p.load_fairness_data()
    
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    
    for protocol in PROTOCOL_ORDER:
        if protocol not in df['Protocol'].unique():
            continue
        subset = df[df['Protocol'] == protocol]
        ax.plot(subset['Round'], subset['Jains_Index'],
                color=COLORS.get(protocol, '#888888'),
                linestyle=LINESTYLES.get(protocol, '-'),
                linewidth=1.0 if protocol == 'Ours' else 0.7,
                label=LABELS.get(protocol, protocol))
    
    # Horizontal line at the 0.90 fairness target
    ax.axhline(y=0.90, color='black', linestyle=':', linewidth=0.5, alpha=0.5)
    ax.text(ax.get_xlim()[1] * 0.95, 0.905, 'Target 0.90',
            fontsize=6, ha='right', va='bottom', alpha=0.5)
    
    ax.set_xlabel('Simulation Round')
    ax.set_ylabel("Jain's Fairness Index")
    ax.set_ylim(0.5, 1.0)
    ax.legend(loc='lower left', ncol=2, frameon=True, fancybox=False,
              edgecolor='black', fontsize=7)
    ax.grid(alpha=0.3, linestyle=':')
    
    plt.tight_layout()
    fig.savefig(figure_path('fig4_load_balancing.png'))
    plt.close()
    print("  Done: fig4_load_balancing.png")


def fig5_delivery_ratio(data_root=None):
    """Fig 5: Packet delivery ratio vs network density."""
    print("Generating Fig 5: Delivery ratio...")
    p = _get_parser(data_root)
    df = p.load_hnd_data()
    
    # Use scale as proxy for density
    scales = sorted(df['Scale'].unique())
    
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    
    for protocol in PROTOCOL_ORDER:
        if protocol not in df['Protocol'].unique():
            continue
        means = []
        for scale in scales:
            subset = df[(df['Protocol'] == protocol) & (df['Scale'] == scale)]
            means.append(subset['DeliveryRatio'].mean())
        ax.plot(scales, means, marker=MARKERS.get(protocol, 'o'),
                color=COLORS.get(protocol, '#888888'),
                linestyle=LINESTYLES.get(protocol, '-'),
                linewidth=1.0, markersize=4, label=LABELS.get(protocol, protocol))
    
    ax.set_xlabel('Network Scale (nodes)')
    ax.set_ylabel('Delivery Ratio')
    ax.set_ylim(0.0, 1.05)
    ax.legend(loc='lower left', ncol=2, frameon=True, fancybox=False,
              edgecolor='black', fontsize=7)
    ax.grid(alpha=0.3, linestyle=':')
    
    plt.tight_layout()
    fig.savefig(figure_path('fig5_delivery_ratio.png'))
    plt.close()
    print("  Done: fig5_delivery_ratio.png")


def fig6_convergence(data_root=None):
    """Fig 6: Convergence behaviour on the 300-node benchmark.

    Three panels: consensus error, gradient norm against the O(1/√k) reference,
    and normalized energy over the control rounds.
    """
    print("Generating Fig 6: Convergence...")
    p = _get_parser(data_root)
    conv_df = p.load_convergence_data()
    ours = conv_df[conv_df['Protocol'] == 'Ours'].groupby('Round').mean(numeric_only=True)
    rounds = ours.index.values
    
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(7.2, 2.4))
    
    # (a) Consensus error
    ax1.plot(rounds, ours['ConsensusError'].values, 'k-', linewidth=0.9)
    ax1.set_ylabel('Consensus Error')
    ax1.set_title('(a) Consensus Error', fontsize=9)
    
    # (b) Gradient norm against the theoretical O(1/√k) bound
    grad_norm = ours['GradientNorm'].values
    ax2.plot(rounds, grad_norm, 'k-', linewidth=0.9, label='Gradient Norm')
    ax2.plot(rounds, grad_norm[0] / np.sqrt(rounds + 1), 'k:', linewidth=0.6,
             label='O(1/√k) bound')
    ax2.set_ylabel('Gradient Norm')
    ax2.set_title('(b) Gradient Norm', fontsize=9)
    ax2.legend(fontsize=6, frameon=True, fancybox=False, edgecolor='black')
    
    # (c) Normalized energy
    ax3.plot(rounds, ours['Normalized_Energy'].values, 'k-', linewidth=0.9)
    ax3.set_ylabel('Normalized Energy')
    ax3.set_title('(c) Normalized Energy', fontsize=9)
    
    for ax in (ax1, ax2, ax3):
        ax.set_xlabel('Round k')
        ax.grid(alpha=0.3, linestyle=':')
        ax.set_xlim(left=0)
    
    plt.tight_layout()
    fig.savefig(figure_path('fig6_convergence.png'))
    plt.close()
    print("  Done: fig6_convergence.png")


def fig7_multi_scale_hnd(data_root=None):
    """Fig 7: Multi-scale HND performance.

    Bars give the HND of our framework and of the DRL-based baseline at the
    four deployment scales, annotated with the relative gain at each scale.
    """
    print("Generating Fig 7: Multi-scale HND...")
    p = _get_parser(data_root)
    df = p.load_hnd_data()
    
    scales = sorted(df['Scale'].unique())
    
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    
    x = np.arange(len(scales))
    width = 0.35
    drl, ours = [], []
    for scale in scales:
        drl.append(df[(df['Protocol'] == 'DeepSensor') & (df['Scale'] == scale)]['HND'].mean())
        ours.append(df[(df['Protocol'] == 'Ours') & (df['Scale'] == scale)]['HND'].mean())
    
    ax.bar(x - width / 2, drl, width, label=LABELS['DeepSensor'], color='#BBBBBB',
           edgecolor='black', linewidth=0.3)
    ax.bar(x + width / 2, ours, width, label='Ours', color='#000000',
           edgecolor='black', linewidth=0.3)
    for xi, d, o in zip(x, drl, ours):
        if d > 0:
            ax.annotate('+%.1f%%' % ((o - d) / d * 100.0), xy=(xi, o),
                        xytext=(0, 4), textcoords='offset points',
                        fontsize=7, ha='center', fontweight='bold')
    
    ax.set_xlabel('Network Scale (nodes)')
    ax.set_ylabel('HND (rounds)')
    ax.set_xticks(x)
    ax.set_xticklabels(scales)
    ax.legend(loc='lower left', bbox_to_anchor=(0.0, 1.01), ncol=2,
              frameon=False, fontsize=7)
    ax.grid(axis='y', alpha=0.3, linestyle=':')
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    fig.savefig(figure_path('fig7_multi_scale_hnd.png'))
    plt.close()
    print("  Done: fig7_multi_scale_hnd.png")


def generate_all(data_root=None):
    """Generate all figures. Returns dict of {figure_name: file_path}."""
    print("=" * 50)
    print("WSN Figures Generation")
    print("=" * 50)
    
    fig_paths = {}
    try:
        fig2_network_lifetime(data_root)
        fig_paths['fig2_network_lifetime'] = str(figure_path('fig2_network_lifetime.png'))
        fig3_energy_consumption(data_root)
        fig_paths['fig3_energy_consumption'] = str(figure_path('fig3_energy_consumption.png'))
        fig4_load_balancing(data_root)
        fig_paths['fig4_load_balancing'] = str(figure_path('fig4_load_balancing.png'))
        fig5_delivery_ratio(data_root)
        fig_paths['fig5_delivery_ratio'] = str(figure_path('fig5_delivery_ratio.png'))
        fig6_convergence(data_root)
        fig_paths['fig6_convergence'] = str(figure_path('fig6_convergence.png'))
        fig7_multi_scale_hnd(data_root)
        fig_paths['fig7_multi_scale_hnd'] = str(figure_path('fig7_multi_scale_hnd.png'))
        print(f"\nAll figures saved to: {figure_path('')}")
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure experiment data has been generated first.")
        print("Run: cd ../WSN-Experiment && python run_experiment.py")
        import traceback
        traceback.print_exc()
    return fig_paths


if __name__ == '__main__':
    generate_all()