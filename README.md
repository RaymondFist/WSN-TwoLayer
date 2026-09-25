## Project Overview

This repository implements a two-layer distributed optimization framework for wireless sensor network energy management, together with the tooling required to reproduce the experimental results. The framework decomposes the global WSN energy management problem into per-node projected gradient descent (Layer 1) coordinated through doubly-stochastic consensus (Layer 2), with online adaptive weight tuning based on residual energy and delivery ratio.

## Architecture

```
WSN-TwoLayer/
├── WSN-Experiment/          # Experiment engine: algorithm implementation + data generation
│   ├── run_experiment.py    # Core Python experiment runner (production)
│   ├── config/default.json  # Default simulation parameters
│   ├── scripts/             # Logging and analysis utilities
│   ├── ns3/                 # NS-3.35 C++ implementation (alternative engine)
│   └── output/              # Generated experiment data (CSV)
│       ├── scale_100/       # 100-node results
│       ├── scale_200/       # 200-node results
│       ├── scale_300/       # 300-node results
│       ├── scale_500/       # 500-node results
│       └── ablation_study.csv
│
├── WSN-Figures/             # Analysis pipeline: statistical analysis + figure/table generation
│   ├── src/
│   │   ├── run_pipeline.py  # Master pipeline orchestrator
│   │   ├── data_parser.py   # Reads experiment CSV data
│   │   ├── paths.py         # Centralized path management
│   │   ├── analysis/        # Statistical analysis (t-test, Cohen's d, CI)
│   │   ├── figures/         # Figure generation (Fig 1-6)
│   │   └── tables/          # Table generation (Table 1-3)
│   ├── requirements.txt     # Python dependencies
│   └── output/              # Generated figures (PNG) and tables (CSV)
│
├── WSN-Hardware/            # TelosB/TinyOS hardware validation
│   ├── generate_figure.py   # Hardware vs simulation comparison chart
│   └── output/              # Hardware measurement data + Fig 7
│
├── deploy.sh                # Cloud server deployment script
├── run_all.sh               # Unified execution pipeline (deploy → experiment → figures)
└── verify_env.py            # Environment verification
```

## Data Flow

```
WSN-Experiment/                    WSN-Figures/                    WSN-Hardware/
─────────────                      ────────────                    ─────────────
Algorithm runs ──→ CSV output ──→ Data parser ──→ Analysis       TelosB testbed
(6 protocols,     (hnd_by_scale,   (pandas)        (scipy)        measurements
 4 scales,        energy_ts,         ↓              ↓              (validation_
 30 runs)         jain_fairness,  Statistical     Figures (PNG)   results.csv)
                  ablation)       analysis        Tables (CSV)          ↓
                                  (p-values,      Statistical     Hardware figure
                                   Cohen's d,     report          (fig7)
                                   CI, rate)                      (generate_figure.py)
```

## Quick Start

### 1. Verify Environment

```bash
python verify_env.py
```

### 2. Run Experiments (Python engine)

```bash
cd WSN-Experiment

# Full experiment: all scales, all protocols, 30 runs
python run_experiment.py --scales 100,200,300,500 --runs 30

# Ablation study only
python run_experiment.py --ablation --runs 30

# Quick test
python run_experiment.py --scales 100 --runs 3 --protocols Ours,LEACH
```

### 3. Generate Figures and Tables

```bash
cd WSN-Figures
pip install -r requirements.txt
python src/run_pipeline.py --data-dir ../WSN-Experiment/output
```

### 4. Run Everything (Linux/macOS)

```bash
bash run_all.sh                    # Full pipeline
bash run_all.sh --runs 3           # Quick test with fewer runs
bash run_all.sh --ablation         # Ablation study only
```

## Alternative: NS-3.35 Engine (Linux only)

The NS-3.35 C++ implementation provides optional packet-level simulation with 802.15.4 PHY/MAC. See [WSN-Experiment/ns3/README.md](WSN-Experiment/ns3/README.md).

```bash
cd WSN-Experiment/ns3
bash setup_ns3.sh    # Install NS-3.35 (~15-30 min)
bash batch_run.sh    # Run experiments
```

## Hardware Model

All experiments use real TelosB node parameters:

| Parameter | Value | Source |
|-----------|-------|--------|
| MCU | MSP430F1611 @ 8 MHz | TelosB datasheet |
| Radio | CC2420 (2.4 GHz) | CC2420 datasheet |
| TX current (0 dBm) | 17.4 mA | CC2420 datasheet |
| TX current (-25 dBm) | 8.5 mA | CC2420 datasheet |
| RX current | 19.7 mA | CC2420 datasheet |
| Idle current | 1.0 mA | CC2420 datasheet |
| Sleep current | 0.001 mA | CC2420 datasheet |
| Voltage | 3.0 V | TelosB spec |
| RAM | 10 kB | MSP430F1611 |
| ROM | 48 kB | MSP430F1611 |

## Output Files

### Experiment Data (CSV)
- `scale_{N}/hnd_by_scale.csv`: HND, energy efficiency, delivery ratio, convergence time, Jain fairness per protocol
- `scale_{N}/energy_timeseries.csv`: Energy consumption over simulation rounds
- `scale_{N}/jain_fairness.csv`: Jain's fairness index over time
- `ablation_study.csv`: Ablation study results (6 variants)

### Figures (PNG, 300 DPI)
- `fig1_network_lifetime.png`: HND comparison across scales
- `fig2_energy_consumption.png`: Energy consumption per round
- `fig3_load_balancing.png`: Jain's fairness over time
- `fig4_delivery_ratio.png`: Delivery ratio vs network density
- `fig5_convergence_rate.png`: Convergence rate analysis
- `fig6_scalability.png`: Scalability (messages + RAM)
- `fig7_hardware_validation.png`: TelosB hardware validation

### Tables (CSV)
- `table1_performance_comparison.csv`: 300-node performance comparison
- `table2_algorithm_characteristics.csv`: Algorithm characteristics
- `table3_ablation_study.csv`: Ablation study results

### Reports
- `statistical_report.txt`: p-values, Cohen's d, confidence intervals, convergence rate

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| η₀ | 0.01 | Initial step size for gradient descent |
| δ | 0.005 | Step size decay rate |
| T_adapt | 50 | Weight adaptation interval (rounds) |
| τ_th | 0.90 | Delivery ratio threshold |
| p_min | -25 dBm | Minimum TX power |
| p_max | 0 dBm | Maximum TX power |
| K_max | 300 | Maximum iterations per run |
| convergence_threshold | 0.002 | Convergence criterion |

## Dependencies

### WSN-Experiment (Python)
- Python 3.8+ (standard library only: `os`, `sys`, `json`, `math`, `random`, `argparse`, `csv`, `pathlib`, `datetime`, `dataclasses`, `typing`)

### WSN-Figures (Python)
- matplotlib ≥ 3.7.0
- numpy ≥ 1.24.0
- pandas ≥ 2.0.0
- scipy ≥ 1.10.0

### WSN-Experiment (NS-3)
- Linux (Ubuntu 20.04/22.04, WSL2)
- NS-3.35
- C++14 compiler (GCC 7+, Clang 5+)