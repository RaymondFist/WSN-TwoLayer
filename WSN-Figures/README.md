# WSN Two-Layer Optimization - Figures & Analysis

Generates publication-quality figures and tables from experiment data.

## Architecture

```
WSN-Figures/
├── requirements.txt
├── src/
│   ├── paths.py                         # Centralized path management
│   ├── data_parser.py                   # Reads experiment CSV output
│   ├── run_pipeline.py                  # Master pipeline runner
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── statistical_analysis.py      # p-values, Cohen's d, CI
│   ├── figures/
│   │   ├── __init__.py
│   │   └── generate_all_figures.py      # Fig 1-7 generation
│   └── tables/
│       ├── __init__.py
│       └── generate_all_tables.py       # Table 1-3 generation
├── output/
│   ├── figures/                         # Generated PNG figures
│   └── tables/                          # Generated CSV tables
└── config/
```

## Data Flow

```
WSN-Experiment/output/scale_*/     WSN-Figures/
─────────────────────────────      ────────────
hnd_by_scale.csv ───────────────→  data_parser.py
energy_timeseries.csv ──────────→    ↓
jain_fairness.csv ──────────────→  statistical_analysis.py
ablation_study.csv ─────────────→    ↓
                                   generate_all_figures.py → Fig 1-7
                                   generate_all_tables.py  → Table 1-3
```

## Usage

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

| Figure | Description | File |
|--------|-------------|------|
| Fig 1 | Network lifetime (HND) across scales | fig1_network_lifetime.png |
| Fig 2 | Energy consumption per round | fig2_energy_consumption.png |
| Fig 3 | Load balancing fairness over time | fig3_load_balancing.png |
| Fig 4 | Delivery ratio vs network density | fig4_delivery_ratio.png |
| Fig 5 | Convergence rate analysis | fig5_convergence_rate.png |
| Fig 6 | Scalability (messages + RAM) | fig6_scalability.png |

### Tables

| Table | Description | File |
|-------|-------------|------|
| Table 1 | Performance comparison (300-node) | table1_performance_comparison.csv |
| Table 2 | Algorithm characteristics | table2_algorithm_characteristics.csv |
| Table 3 | Ablation study results | table3_ablation_study.csv |

## Statistical Analysis

The pipeline automatically computes:
- Welch's t-test with p-values
- Cohen's d effect sizes
- 95% confidence intervals
- Convergence rate estimation (log-log linear regression)
- Super-additive gain analysis