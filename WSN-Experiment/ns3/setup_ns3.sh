#!/bin/bash
# ============================================================================
# NS-3.35 Setup Script for WSN Two-Layer Optimization Experiment
# ============================================================================
# Usage: bash setup_ns3.sh [install_dir]
# Default install directory: ~/ns-allinone-3.35
#
# This script:
# 1. Installs required system dependencies
# 2. Downloads and extracts NS-3.35
# 3. Configures with cmake (LR-WPAN, Energy, FlowMonitor modules)
# 4. Builds NS-3.35
# 5. Copies the WSN simulation script into scratch/
# 6. Builds the simulation
# ============================================================================

set -e

INSTALL_DIR="${1:-$HOME/ns-allinone-3.35}"
NS3_DIR="${INSTALL_DIR}/ns-3.35"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo " NS-3.35 Setup for WSN Two-Layer Optimization Experiment"
echo "============================================================"
echo ""
echo "Install directory: ${INSTALL_DIR}"
echo ""

# ------------------------------------------------------------------
# Step 1: Install system dependencies
# ------------------------------------------------------------------
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential \
    cmake \
    python3 \
    python3-dev \
    git \
    tar \
    wget \
    gcc \
    g++ \
    libgtk-3-dev \
    libxml2-dev \
    libsqlite3-dev \
    libgsl-dev \
    qtbase5-dev \
    2>&1 | tail -1
echo "  Done."

# ------------------------------------------------------------------
# Step 2: Download NS-3.35
# ------------------------------------------------------------------
echo "[2/5] Downloading NS-3.35..."
NS3_TARBALL="${INSTALL_DIR}/ns-allinone-3.35.tar.bz2"

if [ ! -f "${NS3_TARBALL}" ]; then
    mkdir -p "${INSTALL_DIR}"
    wget -q --show-progress \
        "https://www.nsnam.org/releases/ns-allinone-3.35.tar.bz2" \
        -O "${NS3_TARBALL}"
fi

if [ ! -d "${NS3_DIR}" ]; then
    echo "  Extracting..."
    tar -xjf "${NS3_TARBALL}" -C "${INSTALL_DIR}"
fi
echo "  Done."

# ------------------------------------------------------------------
# Step 3: Configure NS-3.35 with cmake
# ------------------------------------------------------------------
echo "[3/5] Configuring NS-3.35 with cmake..."
cd "${NS3_DIR}"

# Configure with required modules
./ns3 configure --enable-examples --enable-tests \
    --enable-modules="core,network,internet,applications,mobility,energy,lr-wpan,spectrum,propagation,flow-monitor,stats" \
    2>&1 | tail -5
echo "  Done."

# ------------------------------------------------------------------
# Step 4: Build NS-3.35
# ------------------------------------------------------------------
echo "[4/5] Building NS-3.35 (this may take 15-30 minutes)..."
./ns3 build 2>&1 | tail -10
echo "  Done."

# ------------------------------------------------------------------
# Step 5: Copy simulation script and build
# ------------------------------------------------------------------
echo "[5/5] Installing WSN simulation..."
cp "${SCRIPT_DIR}/wsn_two_layer_sim.cc" "${NS3_DIR}/scratch/"
echo "  Copied wsn_two_layer_sim.cc to scratch/"

# Rebuild to include the new scratch script
./ns3 build scratch/wsn_two_layer_sim 2>&1 | tail -5
echo "  Done."

echo ""
echo "============================================================"
echo " Setup Complete!"
echo "============================================================"
echo ""
echo "To run the simulation:"
echo "  cd ${NS3_DIR}"
echo "  ./ns3 run scratch/wsn_two_layer_sim -- --nodes=300 --runs=5"
echo ""
echo "For batch experiments:"
echo "  bash ${SCRIPT_DIR}/batch_run.sh ${NS3_DIR}"
echo ""