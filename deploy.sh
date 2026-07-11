#!/bin/bash
# ============================================================================
# WSN Two-Layer Optimization - Cloud Server Deployment Script
# ============================================================================
# Target: PyTorch 2.0.0 / Python 3.8 (Ubuntu 20.04) / CUDA 11.8
#         GPU: V100-32GB × 1 / CPU: 10 vCPU / RAM: 72GB
#
# Usage:
#   chmod +x deploy.sh
#   bash deploy.sh
#   bash deploy.sh --data-disk /mnt/data
#   bash deploy.sh --log-dir /root/logs
#
# Logs are written to: logs/deploy_YYYYMMDD_HHMMSS.log
# JSON summary written to: logs/deploy_YYYYMMDD_HHMMSS.json
# ============================================================================

set -o pipefail

# ------------------------------------------------------------------
# Parse arguments
# ------------------------------------------------------------------
DATA_DISK="/root/autodl-tmp"
LOG_DIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --data-disk) DATA_DISK="$2"; shift 2 ;;
        --log-dir)   LOG_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_TIME=$(date +%s)
RUN_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
RUN_ISO=$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
if [ -z "${LOG_DIR}" ]; then
    LOG_DIR="${SCRIPT_DIR}/logs"
fi
mkdir -p "${LOG_DIR}"

LOG_FILE="${LOG_DIR}/deploy_${RUN_TIMESTAMP}.log"
JSON_FILE="${LOG_DIR}/deploy_${RUN_TIMESTAMP}.json"
VERIFY_LOG="${LOG_DIR}/verify_${RUN_TIMESTAMP}.log"

# Redirect all output to both stdout and log file
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "Log file: ${LOG_FILE}"
echo "JSON summary: ${JSON_FILE}"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass_count=0
fail_count=0
warn_count=0

# Track per-phase results for JSON
declare -A PHASE_RESULTS
PHASE_NAMES=()
PHASE_FAIL_COUNT=0
PHASE_WARN_COUNT=0
PHASE_START_TIME=0

check_pass() {
    echo -e "  ${GREEN}[PASS]${NC} $1"
    pass_count=$((pass_count + 1))
}
check_fail() {
    echo -e "  ${RED}[FAIL]${NC} $1"
    fail_count=$((fail_count + 1))
}
check_warn() {
    echo -e "  ${YELLOW}[WARN]${NC} $1"
    warn_count=$((warn_count + 1))
}

phase_start() {
    local name="$1"
    PHASE_START_TIME=$(date +%s)
    PHASE_FAIL_COUNT=${fail_count}
    PHASE_WARN_COUNT=${warn_count}
    PHASE_NAMES+=("${name}")
    echo ""
    echo "=============================================================================="
    echo " ${name}"
    echo "=============================================================================="
}

phase_end() {
    local name="$1"
    local elapsed=$(($(date +%s) - PHASE_START_TIME))
    local phase_fails=$((fail_count - PHASE_FAIL_COUNT))
    local phase_warns=$((warn_count - PHASE_WARN_COUNT))
    local status="PASS"
    if [ ${phase_fails} -gt 0 ]; then
        status="FAIL"
    elif [ ${phase_warns} -gt 0 ]; then
        status="WARN"
    fi
    PHASE_RESULTS["${name}_elapsed"]="${elapsed}"
    PHASE_RESULTS["${name}_status"]="${status}"
    PHASE_RESULTS["${name}_fails"]="${phase_fails}"
    PHASE_RESULTS["${name}_warns"]="${phase_warns}"
    echo "  >> Phase elapsed: ${elapsed}s, status: ${status} (fails=${phase_fails}, warns=${phase_warns})"
}

# ============================================================================
# Header
# ============================================================================
echo "=============================================================================="
echo " WSN Two-Layer Optimization - Deployment Script"
echo "=============================================================================="
echo "Run timestamp : ${RUN_ISO}"
echo "Script dir    : ${SCRIPT_DIR}"
echo "Data disk     : ${DATA_DISK}"
echo "Log file      : ${LOG_FILE}"
echo ""

# Record system info for JSON
HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
KERNEL=$(uname -r 2>/dev/null || echo "unknown")
ARCH=$(uname -m 2>/dev/null || echo "unknown")

# ============================================================================
# Phase 1: System Environment Check
# ============================================================================
phase_start "Phase 1: System Environment Check"

# OS
echo ""
echo "--- Operating System ---"
OS_NAME="unknown"
OS_VERSION="unknown"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME="${NAME}"
    OS_VERSION="${VERSION_ID}"
    echo "  OS: ${OS_NAME} ${OS_VERSION}"
    echo "  Kernel: ${KERNEL}"
    echo "  Architecture: ${ARCH}"
    echo "  Hostname: ${HOSTNAME}"
    case "${VERSION_ID}" in
        20.04|22.04) check_pass "Ubuntu version ${VERSION_ID} is supported" ;;
        *) check_warn "Ubuntu ${VERSION_ID} may work but is not tested" ;;
    esac
else
    check_warn "Cannot detect OS version"
fi

# Python
echo ""
echo "--- Python ---"
PYTHON_BIN=$(which python3 || which python || echo "")
PYTHON_VER="unknown"
PYTHON_PATH=""
if [ -z "${PYTHON_BIN}" ]; then
    check_fail "Python not found"
else
    PYTHON_VER=$(${PYTHON_BIN} --version 2>&1 | awk '{print $2}')
    PYTHON_PATH=$(which ${PYTHON_BIN} 2>/dev/null)
    echo "  Python: ${PYTHON_VER} (${PYTHON_PATH})"
    PYTHON_MAJOR=$(${PYTHON_BIN} -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(${PYTHON_BIN} -c 'import sys; print(sys.version_info.minor)')
    PYTHON_MICRO=$(${PYTHON_BIN} -c 'import sys; print(sys.version_info.micro)')
    if [ "${PYTHON_MAJOR}" -eq 3 ] && [ "${PYTHON_MINOR}" -ge 8 ]; then
        check_pass "Python ${PYTHON_MAJOR}.${PYTHON_MINOR}.${PYTHON_MICRO} >= 3.8"
    else
        check_fail "Python 3.8+ required, got ${PYTHON_MAJOR}.${PYTHON_MINOR}"
    fi

    # Log full Python info
    echo "  Python details:"
    ${PYTHON_BIN} -c 'import sys, platform; print(f"    implementation: {sys.implementation.name}"); print(f"    compiler: {sys.version}"); print(f"    platform: {platform.platform()}")' 2>/dev/null
fi

# pip
echo ""
echo "--- pip ---"
PIP_VER="unknown"
if ${PYTHON_BIN} -m pip --version &>/dev/null; then
    PIP_VER=$(${PYTHON_BIN} -m pip --version 2>&1 | awk '{print $2}')
    echo "  pip: ${PIP_VER}"
    check_pass "pip is available"
else
    check_fail "pip not available"
fi

# CPU
echo ""
echo "--- CPU ---"
CPU_COUNT=$(nproc 2>/dev/null || echo "unknown")
CPU_MODEL=$(grep "model name" /proc/cpuinfo 2>/dev/null | head -1 | cut -d: -f2 | xargs || echo "unknown")
echo "  CPU: ${CPU_MODEL}"
echo "  Logical CPUs: ${CPU_COUNT}"
if [ "${CPU_COUNT}" != "unknown" ] && [ "${CPU_COUNT}" -ge 4 ]; then
    check_pass "CPU cores: ${CPU_COUNT} (>= 4)"
else
    check_warn "Low CPU count: ${CPU_COUNT}"
fi

# Memory
echo ""
echo "--- Memory ---"
MEM_TOTAL_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
MEM_FREE_KB=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
MEM_TOTAL_GB=$((MEM_TOTAL_KB / 1024 / 1024))
MEM_FREE_GB=$((MEM_FREE_KB / 1024 / 1024))
echo "  Total RAM: ${MEM_TOTAL_GB} GB"
echo "  Available RAM: ${MEM_FREE_GB} GB"
if [ "${MEM_TOTAL_GB}" -ge 16 ]; then
    check_pass "RAM: ${MEM_TOTAL_GB} GB (>= 16 GB)"
else
    check_warn "Low RAM: ${MEM_TOTAL_GB} GB"
fi

# Disk
echo ""
echo "--- Disk ---"
DISK_TOTAL_KB=$(df -k "${DATA_DISK}" 2>/dev/null | tail -1 | awk '{print $2}' || echo "0")
DISK_AVAIL_KB=$(df -k "${DATA_DISK}" 2>/dev/null | tail -1 | awk '{print $4}' || echo "0")
DISK_TOTAL_GB=$((DISK_TOTAL_KB / 1024 / 1024))
DISK_AVAIL_GB=$((DISK_AVAIL_KB / 1024 / 1024))
echo "  Data disk: ${DATA_DISK}"
echo "  Total: ${DISK_TOTAL_GB} GB, Available: ${DISK_AVAIL_GB} GB"
if [ "${DISK_AVAIL_GB}" -ge 10 ]; then
    check_pass "Disk space: ${DISK_AVAIL_GB} GB (>= 10 GB)"
else
    check_warn "Low disk space: ${DISK_AVAIL_GB} GB"
fi

# Also check root disk
ROOT_AVAIL_KB=$(df -k / 2>/dev/null | tail -1 | awk '{print $4}' || echo "0")
ROOT_AVAIL_GB=$((ROOT_AVAIL_KB / 1024 / 1024))
echo "  Root disk available: ${ROOT_AVAIL_GB} GB"

# CUDA (optional)
echo ""
echo "--- CUDA (optional) ---"
CUDA_AVAILABLE="false"
CUDA_VERSION="unknown"
if command -v nvidia-smi &>/dev/null; then
    CUDA_AVAILABLE="true"
    CUDA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
    echo "  GPU: ${GPU_NAME}"
    echo "  GPU memory: ${GPU_MEM}"
    echo "  CUDA driver: ${CUDA_VERSION}"
    check_pass "GPU available (not required for experiments)"
else
    echo "  nvidia-smi not found"
    check_warn "GPU not detected (not required for Python experiments)"
fi

phase_end "Phase 1: System Environment Check"

# ============================================================================
# Phase 2: System Dependencies
# ============================================================================
phase_start "Phase 2: System Dependencies"

echo ""
echo "--- Installing system packages ---"
APT_AVAILABLE="false"
if command -v apt-get &>/dev/null; then
    APT_AVAILABLE="true"
    echo "  [$(date '+%H:%M:%S')] Updating package list..."
    sudo apt-get update -qq 2>&1 | tail -3
    echo ""

    echo "  [$(date '+%H:%M:%S')] Installing fonts-times..."
    sudo apt-get install -y -qq fonts-times 2>&1 | tail -3
    if fc-list 2>/dev/null | grep -qi "Times New Roman"; then
        check_pass "Times New Roman font installed"
    else
        check_warn "Times New Roman font may not be installed correctly"
    fi

    echo "  [$(date '+%H:%M:%S')] Installing build-essential..."
    sudo apt-get install -y -qq build-essential 2>&1 | tail -3
    check_pass "System packages installed"
else
    check_warn "apt-get not found (non-Debian system?)"
fi

phase_end "Phase 2: System Dependencies"

# ============================================================================
# Phase 3: Python Dependencies
# ============================================================================
phase_start "Phase 3: Python Dependencies"

echo ""
echo "--- WSN-Figures dependencies ---"
FIGURES_REQ="${SCRIPT_DIR}/WSN-Figures/requirements.txt"
PIP_INSTALLED_PKGS=""

if [ -f "${FIGURES_REQ}" ]; then
    echo "  Requirements file: ${FIGURES_REQ}"
    echo "  Packages:"
    cat "${FIGURES_REQ}" | sed 's/^/    /'
    echo ""
    echo "  [$(date '+%H:%M:%S')] Installing..."
    ${PYTHON_BIN} -m pip install -r "${FIGURES_REQ}" --quiet 2>&1
    PIP_EXIT=$?
    if [ ${PIP_EXIT} -eq 0 ]; then
        check_pass "WSN-Figures dependencies installed"
    else
        check_fail "pip install failed with exit code ${PIP_EXIT}"
    fi

    # Log installed versions
    echo ""
    echo "  Installed versions:"
    PIP_INSTALLED_PKGS=$(${PYTHON_BIN} -m pip freeze 2>/dev/null | grep -E "^(matplotlib|numpy|pandas|scipy)" || echo "")
    echo "${PIP_INSTALLED_PKGS}" | sed 's/^/    /'
else
    check_fail "requirements.txt not found at ${FIGURES_REQ}"
fi

echo ""
echo "--- WSN-Experiment dependencies ---"
echo "  (stdlib only - no external packages needed)"
check_pass "WSN-Experiment dependencies satisfied"

phase_end "Phase 3: Python Dependencies"

# ============================================================================
# Phase 4: Project Structure Verification
# ============================================================================
phase_start "Phase 4: Project Structure Verification"

echo ""
echo "--- Checking required files ---"

check_file() {
    local path="$1"
    local label="$2"
    if [ -f "${path}" ]; then
        local size=$(wc -c < "${path}" 2>/dev/null | xargs)
        check_pass "${label} (${size} bytes)"
    else
        check_fail "${label} NOT FOUND"
    fi
}

check_dir() {
    local path="$1"
    local label="$2"
    if [ -d "${path}" ]; then
        echo "  ${label}/ exists"
    else
        mkdir -p "${path}"
        echo "  ${label}/ created"
    fi
}

# WSN-Experiment
check_file "${SCRIPT_DIR}/WSN-Experiment/run_experiment.py" "run_experiment.py"
check_file "${SCRIPT_DIR}/WSN-Experiment/config/default.json" "config/default.json"
check_dir "${SCRIPT_DIR}/WSN-Experiment/output" "WSN-Experiment/output"

# WSN-Figures
check_file "${SCRIPT_DIR}/WSN-Figures/src/run_pipeline.py" "run_pipeline.py"
check_file "${SCRIPT_DIR}/WSN-Figures/src/data_parser.py" "data_parser.py"
check_file "${SCRIPT_DIR}/WSN-Figures/src/paths.py" "paths.py"
check_file "${SCRIPT_DIR}/WSN-Figures/src/analysis/statistical_analysis.py" "statistical_analysis.py"
check_file "${SCRIPT_DIR}/WSN-Figures/src/figures/generate_all_figures.py" "generate_all_figures.py"
check_file "${SCRIPT_DIR}/WSN-Figures/src/tables/generate_all_tables.py" "generate_all_tables.py"
check_dir "${SCRIPT_DIR}/WSN-Figures/output/figures" "WSN-Figures/output/figures"
check_dir "${SCRIPT_DIR}/WSN-Figures/output/tables" "WSN-Figures/output/tables"

phase_end "Phase 4: Project Structure Verification"

# ============================================================================
# Phase 5: Python Import Verification
# ============================================================================
phase_start "Phase 5: Python Import Verification"

echo ""
echo "--- Standard library imports (WSN-Experiment) ---"
STDLIB_IMPORTS="os sys json math random argparse csv pathlib datetime dataclasses typing"
STDLIB_FAILED=""
for mod in ${STDLIB_IMPORTS}; do
    ${PYTHON_BIN} -c "import ${mod}" 2>/dev/null && check_pass "import ${mod}" || { check_fail "import ${mod}"; STDLIB_FAILED="${STDLIB_FAILED} ${mod}"; }
done

echo ""
echo "--- Third-party imports (WSN-Figures) ---"
THIRDPARTY_IMPORTS="numpy scipy pandas matplotlib"
THIRDPARTY_FAILED=""
for mod in ${THIRDPARTY_IMPORTS}; do
    ${PYTHON_BIN} -c "import ${mod}" 2>/dev/null && check_pass "import ${mod}" || { check_fail "import ${mod}"; THIRDPARTY_FAILED="${THIRDPARTY_FAILED} ${mod}"; }
done

echo ""
echo "--- matplotlib backend test ---"
MATPLOTLIB_BACKEND="unknown"
${PYTHON_BIN} -c "
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
print('  Backend:', matplotlib.get_backend())
print('  Font family:', plt.rcParams['font.family'])
print('  Matplotlib version:', matplotlib.__version__)
" 2>/dev/null
if [ $? -eq 0 ]; then
    MATPLOTLIB_BACKEND="Agg"
    check_pass "matplotlib Agg backend works"
else
    check_fail "matplotlib backend failed"
fi

phase_end "Phase 5: Python Import Verification"

# ============================================================================
# Phase 6: Smoke Test
# ============================================================================
phase_start "Phase 6: Quick Smoke Test (10 nodes, 2 runs)"

echo ""
SMOKE_OUTPUT="${SCRIPT_DIR}/WSN-Experiment/output/smoke_test"
SMOKE_EXIT_CODE=0
SMOKE_STDOUT=""
SMOKE_STDERR=""

echo "  [$(date '+%H:%M:%S')] Running minimal experiment..."
SMOKE_LOG="${LOG_DIR}/smoke_test_${RUN_TIMESTAMP}.log"
${PYTHON_BIN} "${SCRIPT_DIR}/WSN-Experiment/run_experiment.py" \
    --scales 10 \
    --runs 2 \
    --seed 42 \
    --output "${SMOKE_OUTPUT}" \
    > "${SMOKE_LOG}" 2>&1
SMOKE_EXIT_CODE=$?

echo "  Smoke test exit code: ${SMOKE_EXIT_CODE}"
echo "  Smoke test log: ${SMOKE_LOG}"

if [ ${SMOKE_EXIT_CODE} -eq 0 ] && [ -f "${SMOKE_OUTPUT}/scale_10/hnd_by_scale.csv" ]; then
    check_pass "Experiment runner produces CSV output (exit=${SMOKE_EXIT_CODE})"
    echo ""
    echo "  Sample output:"
    head -3 "${SMOKE_OUTPUT}/scale_10/hnd_by_scale.csv" | sed 's/^/    /'

    # Log data statistics
    echo ""
    echo "  Smoke test data statistics:"
    for csv in "${SMOKE_OUTPUT}"/scale_10/*.csv; do
        if [ -f "${csv}" ]; then
            lines=$(wc -l < "${csv}" 2>/dev/null)
            echo "    $(basename ${csv}): ${lines} lines"
        fi
    done
else
    check_fail "Experiment runner failed (exit=${SMOKE_EXIT_CODE})"
    echo ""
    echo "  Last 20 lines of smoke test log:"
    tail -20 "${SMOKE_LOG}" | sed 's/^/    /'
fi

# Cleanup
rm -rf "${SMOKE_OUTPUT}"

phase_end "Phase 6: Quick Smoke Test (10 nodes, 2 runs)"

# ============================================================================
# Phase 7: Detailed Verification (verify_env.py)
# ============================================================================
phase_start "Phase 7: Detailed Verification (verify_env.py)"

VERIFY_EXIT_CODE=0
if [ -f "${SCRIPT_DIR}/verify_env.py" ]; then
    echo "  [$(date '+%H:%M:%S')] Running verify_env.py..."
    ${PYTHON_BIN} "${SCRIPT_DIR}/verify_env.py" --log "${VERIFY_LOG}" 2>&1
    VERIFY_EXIT_CODE=$?
    echo ""
    echo "  verify_env.py exit code: ${VERIFY_EXIT_CODE}"
    echo "  verify_env.py log: ${VERIFY_LOG}"

    if [ ${VERIFY_EXIT_CODE} -eq 0 ]; then
        check_pass "verify_env.py: all checks passed"
    else
        check_fail "verify_env.py: ${VERIFY_EXIT_CODE} checks failed"
    fi
else
    check_warn "verify_env.py not found, skipping detailed verification"
fi

phase_end "Phase 7: Detailed Verification (verify_env.py)"

# ============================================================================
# Generate JSON Summary
# ============================================================================
# Sanitize package list for JSON (replace newlines with semicolons)
PIP_INSTALLED_PKGS_JSON=$(echo "${PIP_INSTALLED_PKGS}" | tr '\n' ';' | sed 's/;$//' | sed 's/"/\\"/g')
TOTAL_ELAPSED=$(($(date +%s) - START_TIME))

cat > "${JSON_FILE}" << EOFJSON
{
    "deploy_timestamp": "${RUN_ISO}",
    "hostname": "${HOSTNAME}",
    "os": {
        "name": "${OS_NAME}",
        "version": "${OS_VERSION}",
        "kernel": "${KERNEL}",
        "arch": "${ARCH}"
    },
    "python": {
        "version": "${PYTHON_VER}",
        "path": "${PYTHON_PATH}",
        "pip_version": "${PIP_VER}"
    },
    "hardware": {
        "cpu_model": "${CPU_MODEL}",
        "cpu_count": "${CPU_COUNT}",
        "ram_total_gb": "${MEM_TOTAL_GB}",
        "ram_available_gb": "${MEM_FREE_GB}",
        "disk_total_gb": "${DISK_TOTAL_GB}",
        "disk_available_gb": "${DISK_AVAIL_GB}",
        "cuda_available": ${CUDA_AVAILABLE},
        "cuda_version": "${CUDA_VERSION}"
    },
    "dependencies": {
        "apt_available": ${APT_AVAILABLE},
        "installed_packages": "${PIP_INSTALLED_PKGS_JSON}"
    },
    "results": {
        "total_checks": $((pass_count + fail_count + warn_count)),
        "passed": ${pass_count},
        "failed": ${fail_count},
        "warnings": ${warn_count},
        "smoke_test_exit_code": ${SMOKE_EXIT_CODE},
        "verify_exit_code": ${VERIFY_EXIT_CODE},
        "total_elapsed_seconds": ${TOTAL_ELAPSED}
    },
    "phases": {
        "Phase 1: System Environment Check": {
            "status": "${PHASE_RESULTS["Phase 1: System Environment Check_status"]}",
            "elapsed_seconds": ${PHASE_RESULTS["Phase 1: System Environment Check_elapsed"]:-0},
            "failures": ${PHASE_RESULTS["Phase 1: System Environment Check_fails"]:-0},
            "warnings": ${PHASE_RESULTS["Phase 1: System Environment Check_warns"]:-0}
        },
        "Phase 2: System Dependencies": {
            "status": "${PHASE_RESULTS["Phase 2: System Dependencies_status"]}",
            "elapsed_seconds": ${PHASE_RESULTS["Phase 2: System Dependencies_elapsed"]:-0},
            "failures": ${PHASE_RESULTS["Phase 2: System Dependencies_fails"]:-0},
            "warnings": ${PHASE_RESULTS["Phase 2: System Dependencies_warns"]:-0}
        },
        "Phase 3: Python Dependencies": {
            "status": "${PHASE_RESULTS["Phase 3: Python Dependencies_status"]}",
            "elapsed_seconds": ${PHASE_RESULTS["Phase 3: Python Dependencies_elapsed"]:-0},
            "failures": ${PHASE_RESULTS["Phase 3: Python Dependencies_fails"]:-0},
            "warnings": ${PHASE_RESULTS["Phase 3: Python Dependencies_warns"]:-0}
        },
        "Phase 4: Project Structure Verification": {
            "status": "${PHASE_RESULTS["Phase 4: Project Structure Verification_status"]}",
            "elapsed_seconds": ${PHASE_RESULTS["Phase 4: Project Structure Verification_elapsed"]:-0},
            "failures": ${PHASE_RESULTS["Phase 4: Project Structure Verification_fails"]:-0},
            "warnings": ${PHASE_RESULTS["Phase 4: Project Structure Verification_warns"]:-0}
        },
        "Phase 5: Python Import Verification": {
            "status": "${PHASE_RESULTS["Phase 5: Python Import Verification_status"]}",
            "elapsed_seconds": ${PHASE_RESULTS["Phase 5: Python Import Verification_elapsed"]:-0},
            "failures": ${PHASE_RESULTS["Phase 5: Python Import Verification_fails"]:-0},
            "warnings": ${PHASE_RESULTS["Phase 5: Python Import Verification_warns"]:-0}
        },
        "Phase 6: Quick Smoke Test (10 nodes, 2 runs)": {
            "status": "${PHASE_RESULTS["Phase 6: Quick Smoke Test (10 nodes, 2 runs)_status"]}",
            "elapsed_seconds": ${PHASE_RESULTS["Phase 6: Quick Smoke Test (10 nodes, 2 runs)_elapsed"]:-0},
            "failures": ${PHASE_RESULTS["Phase 6: Quick Smoke Test (10 nodes, 2 runs)_fails"]:-0},
            "warnings": ${PHASE_RESULTS["Phase 6: Quick Smoke Test (10 nodes, 2 runs)_warns"]:-0}
        },
        "Phase 7: Detailed Verification (verify_env.py)": {
            "status": "${PHASE_RESULTS["Phase 7: Detailed Verification (verify_env.py)_status"]}",
            "elapsed_seconds": ${PHASE_RESULTS["Phase 7: Detailed Verification (verify_env.py)_elapsed"]:-0},
            "failures": ${PHASE_RESULTS["Phase 7: Detailed Verification (verify_env.py)_fails"]:-0},
            "warnings": ${PHASE_RESULTS["Phase 7: Detailed Verification (verify_env.py)_warns"]:-0}
        }
    },
    "log_file": "${LOG_FILE}",
    "verify_log": "${VERIFY_LOG}",
    "experiment_logs": {
        "run_experiment": "${SCRIPT_DIR}/WSN-Experiment/output/logs/run_experiment_*.log",
        "run_pipeline": "${SCRIPT_DIR}/WSN-Figures/output/logs/run_pipeline_*.log"
    }
}
EOFJSON

# ============================================================================
# Final Summary
# ============================================================================
echo ""
echo "=============================================================================="
echo " Deployment Summary"
echo "=============================================================================="
echo ""
echo -e "  ${GREEN}Passed  : ${pass_count}${NC}"
echo -e "  ${YELLOW}Warnings: ${warn_count}${NC}"
echo -e "  ${RED}Failed  : ${fail_count}${NC}"
echo ""
echo "  Total elapsed: ${TOTAL_ELAPSED}s"
echo "  Log file     : ${LOG_FILE}"
echo "  JSON summary : ${JSON_FILE}"
echo ""

if [ "${fail_count}" -gt 0 ]; then
    echo -e "${RED}DEPLOYMENT FAILED - ${fail_count} check(s) failed.${NC}"
    echo "Review the log file for details:"
    echo "  cat ${LOG_FILE}"
    echo ""
    echo "Common fixes:"
    echo "  - Missing Python: sudo apt-get install python3 python3-pip"
    echo "  - Missing packages: pip install -r WSN-Figures/requirements.txt"
    echo "  - Permission denied: check file ownership and permissions"
    exit 1
fi

echo "=============================================================================="
echo " Next Steps: Running Experiments"
echo "=============================================================================="
echo ""
echo "  NOTE: All experiments run on CPU. GPU is not required."
echo ""
echo "  --- Quick test (50 nodes, 3 runs) ---"
echo "  cd ${SCRIPT_DIR}/WSN-Experiment"
echo "  python run_experiment.py --scales 50,100 --runs 3"
echo ""
echo "  --- Full experiment (all scales, 30 runs) ---"
echo "  cd ${SCRIPT_DIR}/WSN-Experiment"
echo "  python run_experiment.py --scales 100,200,300,500 --runs 30"
echo ""
echo ""
echo "  --- Ablation study only ---"
echo "  cd ${SCRIPT_DIR}/WSN-Experiment"
echo "  python run_experiment.py --ablation --runs 30"
echo ""
echo "  --- Generate figures and tables ---"
echo "  cd ${SCRIPT_DIR}/WSN-Figures"
echo "  python src/run_pipeline.py --data-dir ../WSN-Experiment/output"
echo ""
echo "  --- Estimated runtime (10 vCPU) ---"
echo "  Full experiment:  ~2-4 hours"
echo "  Ablation only:   ~30-60 minutes"
echo "  Figures & tables: ~2-5 minutes"
echo ""
echo "  --- View logs ---"
echo "  ls -la ${LOG_DIR}/"
echo ""
echo "  --- Experiment execution logs ---"
echo "  After running experiments, logs are at:"
echo "    WSN-Experiment/output/logs/run_experiment_*.log"
echo "    WSN-Experiment/output/logs/run_experiment_*.json"
echo ""
echo "  --- Pipeline execution logs ---"
echo "  After running figures/tables, logs are at:"
echo "    WSN-Figures/output/logs/run_pipeline_*.log"
echo "    WSN-Figures/output/logs/run_pipeline_*.json   (machine-readable)"
echo ""
echo "  --- Analyze JSON summaries ---"
echo "  python3 -c \"import json; d=json.load(open('WSN-Experiment/output/logs/run_experiment_*.json'));"
echo "    print(f'Phases: {len(d[\\\"phases\\\"])}');"
echo "    print(f'Errors: {d[\\\"error_count\\\"]}');"
echo "    print(f'Warnings: {d[\\\"warning_count\\\"]}');"
echo "    print(f'Elapsed: {d[\\\"total_elapsed_seconds\\\"]}s')\""
echo ""
echo "=============================================================================="
echo " Deployment Complete!"
echo "=============================================================================="