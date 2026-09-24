# NS-3.35 WSN Experiment Setup

This directory contains everything needed to run the WSN two-layer optimization
experiment in NS-3.35.

## Prerequisites

- **Linux environment** (WSL2 / Ubuntu 22.04+ / native Linux)
- At least 4 GB of free memory (required to build NS-3.35)
- About 2 GB of disk space (NS-3.35 + build artifacts)

## Quick Start

### 1. Install WSL Ubuntu (if not already installed)

```powershell
# Run in Windows PowerShell (administrator privileges)
wsl --install -d Ubuntu-22.04
```

Restart and open the Ubuntu terminal.

### 2. Copy the scripts into WSL

```bash
# In the WSL Ubuntu shell
cp -r /mnt/d/Workspace/JavaSource/Repositories/ProductLine/SCI-Title/SCI-Session02/WSN-TwoLayer/WSN-Experiment/ns3/ ~/wsn-ns3/
cd ~/wsn-ns3/
```

### 3. Install and build NS-3.35

```bash
bash setup_ns3.sh
```

This step takes 15-30 minutes (compiling NS-3.35).

### 4. Run the experiment

```bash
# Full experiment (4 scales x 6 protocols x 30 runs)
bash batch_run.sh

# Or run manually
cd ~/ns-allinone-3.35/ns-3.35
./ns3 run scratch/wsn_two_layer_sim -- --scales=100,200,300,500 --runs=30 --output=output/
```

### 5. Copy the results back to Windows

```bash
cp -r ~/ns-allinone-3.35/ns-3.35/output/ /mnt/d/Workspace/JavaSource/Repositories/ProductLine/SCI-Title/SCI-Session02/WSN-TwoLayer/WSN-Experiment/output/
```

## Hardware Model

The simulation uses real TelosB node parameters:

| Parameter | Value | Source |
|-----------|-------|--------|
| TX current (0 dBm) | 17.4 mA | CC2420 datasheet |
| TX current (-25 dBm) | 8.5 mA | CC2420 datasheet |
| RX current | 19.7 mA | CC2420 datasheet |
| Idle current | 1.0 mA | CC2420 datasheet |
| Sleep current | 0.001 mA | CC2420 datasheet |
| Voltage | 3.0 V | TelosB spec |
| Initial energy | 2.5 J | 2xAA batteries |
| RAM | 10 kB | MSP430F1611 |
| ROM | 48 kB | MSP430F1611 |

## Output Format

The output CSV files are fully compatible with the WSN-Figures pipeline:

```
output/
├── scale_100/
│   ├── hnd_by_scale.csv        # HND, energy efficiency, delivery ratio, convergence time, fairness
│   ├── energy_timeseries.csv   # Energy consumption time series
│   └── jain_fairness.csv       # Jain's fairness index
├── scale_200/
├── scale_300/
├── scale_500/
├── ablation_study.csv          # Ablation study
└── run_metadata.json           # Run metadata
```

## Differences from the Python Implementation

| Aspect | Python implementation | NS-3.35 implementation |
|--------|-----------------------|------------------------|
| Algorithm | Identical | Identical |
| Topology | Geometric random graph | Geometric random graph |
| Energy model | CC2420 parameters | CC2420 parameters |
| Channel model | SNR formula | Log-distance + Nakagami fading |
| MAC layer | None | 802.15.4 CSMA/CA (optional) |
| Packet-level simulation | No | Supported (must be enabled) |
| Reproducibility | Seed controlled | Seed controlled |
| Platform | Cross-platform | Linux only |

## Enabling Full NS-3 Network Simulation

The current implementation uses algorithm-level simulation for speed. To enable
the full 802.15.4 packet-level simulation in NS-3, change the
`USE_NS3_NETWORKING` macro in `wsn_two_layer_sim.cc`:

```cpp
#define USE_NS3_NETWORKING 1  // enable the NS-3 network stack
```

Packet-level simulation significantly increases runtime (300 nodes x 200
iterations takes a few hours).