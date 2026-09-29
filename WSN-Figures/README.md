# WSN Two-Layer Optimization - Figures & Analysis Pipeline

Generates figures and tables from the experiment data.

## Architecture

```
WSN-Figures/
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── paths.py                         # Centralized path management
│   ├── data_parser.py                   # Reads experiment CSV output
│   ├── pipeline_logger.py               # Dual-output logger (console + JSON)
│   ├── run_pipeline.py                  # Master pipeline orchestrator
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── statistical_analysis.py      # p-values, Cohen's d, CI, convergence rate
│   ├── figures/
│   │   ├── __init__.py
│   │   └── generate_all_figures.py      # Fig 2-7 generation
│   └── tables/
│       ├── __init__.py
│       └── generate_all_tables.py       # Table 1-3 generation
├── output/
│   ├── figures/                         # Generated PNG figures (300 DPI)
│   │   ├── fig1_architecture.png        # Two-layer architecture schematic (static asset)
│   │   ├── fig2_network_lifetime.png
│   │   ├── fig3_energy_consumption.png
│   │   ├── fig4_load_balancing.png
│   │   ├── fig5_delivery_ratio.png
│   │   ├── fig6_convergence.png
│   │   └── fig7_multi_scale_hnd.png
│   ├── tables/                          # Generated CSV tables
│   │   ├── table1_performance_comparison.csv
│   │   ├── table2_algorithm_characteristics.csv
│   │   └── table3_ablation_study.csv
│   ├── logs/                            # Execution logs (auto-generated)
│   └── statistical_report.txt           # Full statistical analysis report
└── README.md
```

## Data Flow

```
WSN-Experiment/output/scale_*/     WSN-Figures/
─────────────────────────────      ────────────
hnd_by_scale.csv ───────────────→  data_parser.py
energy_timeseries.csv ──────────→    ↓
jain_fairness.csv ──────────────→  statistical_analysis.py  → statistical_report.txt
convergence_data.csv ───────────→    ↓
ablation_study.csv ─────────────→  generate_all_figures.py  → Fig 2-7 (PNG)
                                   generate_all_tables.py   → Table 1-3 (CSV)
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate everything (figures + tables + statistical report)
python src/run_pipeline.py

# Figures only
python src/run_pipeline.py --figures

# Tables only
python src/run_pipeline.py --tables

# Statistical report only
python src/run_pipeline.py --report

# Use custom data directory
python src/run_pipeline.py --data-dir ../WSN-Experiment/output/
```

## Output

### Figures (300 DPI, grayscale-compatible)

| Figure | Description | Source Function |
|--------|-------------|-----------------|
| Fig 1 | Two-layer architecture schematic | static asset (not generated) |
| Fig 2 | Network lifetime (HND) across scales | `fig2_network_lifetime()` |
| Fig 3 | Energy consumption per round | `fig3_energy_consumption()` |
| Fig 4 | Load balancing (Jain's fairness) over time | `fig4_load_balancing()` |
| Fig 5 | Delivery ratio vs network density | `fig5_delivery_ratio()` |
| Fig 6 | Convergence behaviour (error, gradient norm, energy) | `fig6_convergence()` |
| Fig 7 | Multi-scale HND (Ours vs DRL-based) | `fig7_multi_scale_hnd()` |

Note: Fig 8 (hardware validation) is generated separately by `WSN-Hardware/generate_figure.py`.

### Tables

| Table | Description | Source Function |
|-------|-------------|-----------------|
| Table 1 | Performance comparison (300-node, 30 runs) | `table1_performance_comparison()` |
| Table 2 | Algorithm characteristics (RAM, ROM, convergence) | `table2_algorithm_characteristics()` |
| Table 3 | Ablation study results (6 variants) | `table3_ablation_study()` |
| Table 4 | Hardware validation (15-node TelosB) | `WSN-Hardware/output/validation_results.csv` |

### Statistical Report

The pipeline automatically computes:
- Welch's t-test with p-values (Ours vs each baseline)
- Cohen's d effect sizes
- 95% confidence intervals
- Super-additive gain analysis (synergy between Layer 2 and adaptive weights)
- Convergence rate estimation via log-log linear regression

## Style Configuration

All figures use:
- Font: Times New Roman, serif
- Resolution: 300 DPI
- Grayscale-compatible color palette
- Distinct line styles and markers per protocol
- Single-column (3.5 inch) and double-column (7 inch) widths

## Dependencies

| Package | Minimum Version |
|---------|----------------|
| matplotlib | 3.7.0 |
| numpy | 1.24.0 |
| pandas | 2.0.0 |
| scipy | 1.10.0 |