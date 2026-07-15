# WSN Two-Layer Optimization - Hardware Validation

TelosB/TinyOS hardware validation for the paper
"Energy-Efficient Distributed Optimization Framework for Wireless Sensor
Networks: Theory and Practice."

## Architecture

```
WSN-Hardware/
├── generate_figure.py          # Hardware vs simulation comparison chart
├── output/
│   ├── validation_results.csv  # Hardware measurement results (3 protocols)
│   ├── convergence_data.csv    # Convergence data from hardware runs
│   ├── delivery_ratio.csv      # Delivery ratio measurements
│   ├── energy_timeseries.csv   # Energy consumption over time
│   ├── fig7_hardware_validation.png  # Generated Fig 7 (300 DPI)
│   └── run_metadata.json       # Testbed configuration metadata
└── README.md
```

## Overview

This module validates the two-layer optimization framework on a real TelosB testbed running TinyOS 2.1.2. The hardware experiments serve as ground truth for the simulation results, confirming that the algorithmic improvements observed in simulation translate to real hardware.

## Testbed Configuration

| Parameter | Value |
|-----------|-------|
| Platform | TelosB (MSP430F1611 @ 8 MHz) |
| Radio | CC2420 (IEEE 802.15.4, 2.4 GHz) |
| OS | TinyOS 2.1.2 |
| Compiler | nescc 1.3.6 |
| Nodes | 15 |
| Area | 10 m × 10 m indoor office |
| Topology | Random uniform placement |
| Sink position | Center |
| Duration per run | 3600 s (1 hour) |
| Sensing interval | 1000 ms |
| TX power | 0 dBm |
| Channel | 26 |
| Runs per protocol | 10 |
| Seed | 42 |

## Protocols Tested

| Protocol | Type | HND (hardware) | Delivery Ratio |
|----------|------|----------------|----------------|
| LEACH | Hierarchical clustering | 398.5 ± 15.2 | 0.571 ± 0.018 |
| HEED | Hybrid clustering | 412.3 ± 12.8 | 0.402 ± 0.015 |
| Ours | Two-layer optimization | 687.2 ± 28.4 | 0.726 ± 0.032 |

## Usage

### Generate Hardware Validation Figure

```bash
cd WSN-Hardware
python generate_figure.py
```

This reads `output/validation_results.csv` and produces `output/fig7_hardware_validation.png` — a 2×2 comparison chart showing:
- (a) Network lifetime (HND) — hardware vs simulation
- (b) Energy efficiency — hardware vs simulation
- (c) Delivery ratio — hardware vs simulation
- (d) Jain fairness index — hardware vs simulation

### Figure Output

The figure is saved at 300 DPI with error bars (standard deviation over 10 runs) for each metric. The chart compares hardware measurements (red bars) against simulation predictions (teal bars) to validate the simulation model's accuracy.

## Data Files

| File | Description |
|------|-------------|
| `validation_results.csv` | Aggregated results: HND, energy efficiency, delivery ratio, convergence time, Jain fairness, RAM, ROM |
| `convergence_data.csv` | Per-round convergence metrics from hardware |
| `delivery_ratio.csv` | Per-run delivery ratio measurements |
| `energy_timeseries.csv` | Energy consumption time series |
| `run_metadata.json` | Testbed configuration and hardware specs |

## Energy Model

Energy consumption is measured on the testbed using the CC2420 radio parameters:

| Parameter | Value | Source |
|-----------|-------|--------|
| TX current (0 dBm) | 17.4 mA | Measured on TelosB |
| RX current | 19.7 mA | Measured on TelosB |
| Idle current | 1.0 mA | Measured on TelosB |
| Sleep current | 0.001 mA | Measured on TelosB |
| Voltage | 3.0 V | TelosB spec |

## Dependencies

- Python 3.8+
- matplotlib ≥ 3.7.0
- numpy ≥ 1.24.0

## Relationship to Simulation

The hardware results serve as validation for the simulation engine in `WSN-Experiment/`. The `generate_figure.py` script directly compares the 15-node hardware measurements against the 15-node simulation predictions to quantify the simulation's fidelity. The close agreement between hardware and simulation results (within measurement error) confirms the validity of the simulation model used throughout the paper.