# WSN Two-Layer Optimization - Experiment Engine

Implements the two-layer distributed optimization framework from the paper
"Energy-Efficient Distributed Optimization Framework for Wireless Sensor
Networks: Theory and Practice."

## Architecture

```
WSN-Experiment/
├── run_experiment.py        # Core experiment runner (Python)
├── config/
│   └── default.json         # Default simulation parameters
├── scripts/
│   └── batch_run.py         # Batch experiment runner
├── output/                  # Generated experiment data (CSV)
│   ├── scale_100/           # 100-node results
│   ├── scale_200/           # 200-node results
│   ├── scale_300/           # 300-node results
│   └── scale_500/           # 500-node results
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
                 ablation_study.csv)
```

## Hardware Model

TelosB: MSP430 @ 8 MHz, CC2420 radio, 10 kB RAM, 48 kB flash
- TX: 17.4 mA @ 0 dBm, 8.5 mA @ -25 dBm (CC2420 datasheet curve)
- RX: 19.7 mA, Idle: 1.0 mA, Sleep: 0.001 mA
- Voltage: 3.0V

## Run

### Python (cross-platform, faster)

```bash
# All protocols at all scales
python run_experiment.py --scales 100,200,300,500 --runs 30

# Ablation study
python run_experiment.py --ablation --runs 30

# Specific protocol
python run_experiment.py --scales 300 --protocols Ours,LEACH --runs 30
```

### NS-3.35 (Linux, more realistic PHY/MAC)

详见 [ns3/README.md](ns3/README.md)

```bash
# Setup (Linux only)
cd ns3/ && bash setup_ns3.sh

# Run experiments
bash batch_run.sh
```

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| eta_0 | 0.01 | Initial step size |
| delta | 0.005 | Step size decay rate |
| T_adapt | 50 | Adaptation interval |
| tau_th | 0.90 | Delivery ratio threshold |
| p_min | -25 dBm | Min TX power |
| p_max | 0 dBm | Max TX power |
| K_max | 200 | Max iterations |