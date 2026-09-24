# WSN Two-Layer Optimization - Experiment Engine

Implements the two-layer distributed optimization framework: per-node projected
gradient descent coordinated through doubly-stochastic consensus, with online
adaptive weight tuning.

## Architecture

```
WSN-Experiment/
├── run_experiment.py        # Core experiment runner (Python)
├── config/
│   └── default.json         # Default simulation parameters
├── scripts/
│   ├── __init__.py           # Package marker
│   ├── experiment_logger.py  # Dual-output logger (console + JSON)
│   └── analyze_logs.py       # Post-run log analysis tool
├── ns3/                      # NS-3.35 C++ implementation (alternative engine)
│   ├── README.md
│   ├── setup_ns3.sh
│   ├── batch_run.sh
│   └── wsn_two_layer_sim.cc
├── output/                   # Generated experiment data (CSV)
│   ├── scale_100/            # 100-node results
│   ├── scale_200/            # 200-node results
│   ├── scale_300/            # 300-node results
│   ├── scale_500/            # 500-node results
│   ├── ablation_study.csv
│   └── run_metadata.json
└── README.md
```

## Data Flow

```
WSN-Experiment/                    WSN-Figures/
─────────────                      ────────────
Algorithm runs → CSV output ────→  Data parser → Statistical analysis
                (hnd_by_scale.csv,              → Figures (PNG)
                 energy_timeseries.csv,         → Tables (CSV)
                 jain_fairness.csv,
                 convergence_data.csv,
                 ablation_study.csv)
```

## Hardware Model

TelosB: MSP430F1611 @ 8 MHz, CC2420 radio, 10 kB RAM, 48 kB flash
- TX: 17.4 mA @ 0 dBm, 8.5 mA @ -25 dBm (CC2420 datasheet curve)
- RX: 19.7 mA, Idle: 1.0 mA, Sleep: 0.001 mA
- Voltage: 3.0 V, Initial energy: 2.5 J (2×AA batteries)

## Quick Start

### Python Engine (cross-platform, recommended)

```bash
# Full experiment: 4 scales × 6 protocols × 30 runs
python run_experiment.py --scales 100,200,300,500 --runs 30

# Ablation study only (300 nodes)
python run_experiment.py --ablation --runs 30

# Quick test (single scale, limited protocols)
python run_experiment.py --scales 100 --runs 3 --protocols Ours,LEACH

# Custom output directory
python run_experiment.py --scales 100,200,300,500 --runs 30 --output /path/to/output
```

### NS-3.35 Engine (Linux only, realistic PHY/MAC)

See [ns3/README.md](ns3/README.md) for detailed instructions.

```bash
cd ns3/
bash setup_ns3.sh      # Install and build NS-3.35 (~15-30 min)
bash batch_run.sh       # Run full experiment suite
```

### Analyze Experiment Logs

After running experiments, use the log analysis tool:

```bash
python scripts/analyze_logs.py output/logs/
python scripts/analyze_logs.py output/logs/ --detail
```

## Output Format

Each scale directory contains:

| File | Columns | Description |
|------|---------|-------------|
| `hnd_by_scale.csv` | Protocol, Scale, Run, HND, EnergyEfficiency, DeliveryRatio, ConvergenceTime_ms, JainsFairness, RamKB, RomKB | Per-run protocol results |
| `energy_timeseries.csv` | Protocol, Round, NodeID, Energy_mW, Normalized_Energy | Energy consumption over time |
| `jain_fairness.csv` | Protocol, Round, Jains_Index | Jain's fairness index over time |
| `convergence_data.csv` | Protocol, Round, ConsensusError, GradientNorm, Normalized_Energy | Convergence metrics (Ours only) |

Root-level:

| File | Description |
|------|-------------|
| `ablation_study.csv` | Ablation study results (6 variants) |
| `run_metadata.json` | Experiment metadata (timestamp, hardware model, seed) |

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| η₀ | 0.01 | Initial step size |
| δ | 0.005 | Step size decay rate |
| T_adapt | 50 | Weight adaptation interval (rounds) |
| τ_th | 0.90 | Delivery ratio threshold |
| τ_min | 0.10 | Minimum duty cycle |
| p_min | -25 dBm | Minimum TX power |
| p_max | 0 dBm | Maximum TX power |
| K_max | 300 | Maximum iterations per run |
| convergence_threshold | 0.002 | Convergence criterion |

## Protocols

| Protocol | Type | Description |
|----------|------|-------------|
| LEACH | Hierarchical clustering | Low-Energy Adaptive Clustering Hierarchy |
| HEED | Hybrid clustering | Hybrid Energy-Efficient Distributed clustering |
| PEGASIS | Chain-based | Power-Efficient Gathering in Sensor Information Systems |
| DeepSensor | DRL-based | Deep reinforcement learning for sensor scheduling |
| FL-Energy | Federated learning | Federated learning for energy optimization |
| Ours | Two-layer optimization | Layer 1 gradient descent + Layer 2 consensus |

## Dependencies

- Python 3.8+ (standard library only)
- No external packages required

## Logging

The experiment runner uses `scripts/experiment_logger.py` to produce:
- Timestamped log files in `output/logs/run_experiment_YYYYMMDD_HHMMSS.log`
- JSON summary files in `output/logs/run_experiment_YYYYMMDD_HHMMSS.json`

Use `scripts/analyze_logs.py` to parse and inspect these logs.