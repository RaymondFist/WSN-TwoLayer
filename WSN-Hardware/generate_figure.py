"""Generate hardware validation figure comparing hardware vs simulation results."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import csv
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

# Read validation results
hw_data = {}
with open(os.path.join(OUTPUT_DIR, 'validation_results.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        hw_data[row['Protocol']] = {
            'hnd': float(row['HND (mean)']),
            'hnd_std': float(row['HND (std)']),
            'ee': float(row['Energy Eff. (mean)']),
            'delivery': float(row['Del. Ratio (mean)']),
            'delivery_std': float(row['Del. Ratio (std)']),
            'jain': float(row['Jain Fairness']),
        }

# Simulation data at 15-node scale (from run_metadata, consistent with 100-node trends)
sim_data = {
    'LEACH': {'hnd': 410.2, 'hnd_std': 12.8, 'ee': 0.101, 'delivery': 0.568, 'jain': 0.788},
    'HEED': {'hnd': 425.5, 'hnd_std': 10.3, 'ee': 0.075, 'delivery': 0.395, 'jain': 0.930},
    'Ours':  {'hnd': 698.5, 'hnd_std': 22.1, 'ee': 0.242, 'delivery': 0.732, 'jain': 0.985},
}

protocols = ['LEACH', 'HEED', 'Ours']
colors = ['#E8A87C', '#95E1D3', '#F38181']
x = np.arange(len(protocols))
width = 0.35

fig, axes = plt.subplots(2, 2, figsize=(10, 8))
fig.suptitle('Hardware Validation: TelosB Testbed (15 nodes, 10 runs)', fontsize=13, fontweight='bold')

# (a) HND comparison
ax = axes[0, 0]
hw_hnd = [hw_data[p]['hnd'] for p in protocols]
hw_hnd_err = [hw_data[p]['hnd_std'] for p in protocols]
sim_hnd = [sim_data[p]['hnd'] for p in protocols]
sim_hnd_err = [sim_data[p]['hnd_std'] for p in protocols]
bars1 = ax.bar(x - width/2, hw_hnd, width, yerr=hw_hnd_err, label='Hardware', color='#F38181', capsize=4, edgecolor='black', linewidth=0.5)
bars2 = ax.bar(x + width/2, sim_hnd, width, yerr=sim_hnd_err, label='Simulation', color='#95E1D3', capsize=4, edgecolor='black', linewidth=0.5)
ax.set_ylabel('HND (rounds)')
ax.set_title('(a) Network Lifetime (HND)')
ax.set_xticks(x)
ax.set_xticklabels(protocols)
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)

# (b) Energy efficiency
ax = axes[0, 1]
hw_ee = [hw_data[p]['ee'] for p in protocols]
sim_ee = [sim_data[p]['ee'] for p in protocols]
ax.bar(x - width/2, hw_ee, width, label='Hardware', color='#F38181', edgecolor='black', linewidth=0.5)
ax.bar(x + width/2, sim_ee, width, label='Simulation', color='#95E1D3', edgecolor='black', linewidth=0.5)
ax.set_ylabel('Energy Efficiency')
ax.set_title('(b) Energy Efficiency')
ax.set_xticks(x)
ax.set_xticklabels(protocols)
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)

# (c) Delivery ratio
ax = axes[1, 0]
hw_dr = [hw_data[p]['delivery'] for p in protocols]
hw_dr_err = [hw_data[p]['delivery_std'] for p in protocols]
sim_dr = [sim_data[p]['delivery'] for p in protocols]
ax.bar(x - width/2, hw_dr, width, yerr=hw_dr_err, label='Hardware', color='#F38181', capsize=4, edgecolor='black', linewidth=0.5)
ax.bar(x + width/2, sim_dr, width, label='Simulation', color='#95E1D3', edgecolor='black', linewidth=0.5)
ax.set_ylabel('Delivery Ratio')
ax.set_title('(c) Delivery Ratio')
ax.set_xticks(x)
ax.set_xticklabels(protocols)
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)

# (d) Jain fairness
ax = axes[1, 1]
hw_jain = [hw_data[p]['jain'] for p in protocols]
sim_jain = [sim_data[p]['jain'] for p in protocols]
ax.bar(x - width/2, hw_jain, width, label='Hardware', color='#F38181', edgecolor='black', linewidth=0.5)
ax.bar(x + width/2, sim_jain, width, label='Simulation', color='#95E1D3', edgecolor='black', linewidth=0.5)
ax.set_ylabel('Jain Fairness Index')
ax.set_title('(d) Jain Fairness')
ax.set_xticks(x)
ax.set_xticklabels(protocols)
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 1.05)

plt.tight_layout()
fig_path = os.path.join(OUTPUT_DIR, 'fig7_hardware_validation.png')
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
plt.close()
print(f'Figure saved: {fig_path}')