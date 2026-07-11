#!/bin/bash
# ============================================================================
# Batch Run Script for WSN Two-Layer Optimization Experiments (NS-3.35)
# ============================================================================
# Usage: bash batch_run.sh [ns3_dir]
#   ns3_dir: Path to ns-3.35 installation (default: ~/ns-allinone-3.35/ns-3.35)
#
# Runs the full experiment suite:
#   - 4 network scales: 100, 200, 300, 500 nodes
#   - 6 protocols: LEACH, HEED, PEGASIS, DeepSensor, FL-Energy, Ours
#   - 30 runs per configuration
#   - Ablation study at 300 nodes
#   - Output CSV files compatible with WSN-Figures pipeline
#
# Logs are written to: logs/ns3_batch_YYYYMMDD_HHMMSS.log
# JSON summary written to: logs/ns3_batch_YYYYMMDD_HHMMSS.json
# ============================================================================

set -o pipefail

NS3_DIR="${1:-$HOME/ns-allinone-3.35/ns-3.35}"
OUTPUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/output"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

START_TIME=$(date +%s)
RUN_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
RUN_ISO=$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
LOG_DIR="${SCRIPT_DIR}/../logs"
mkdir -p "${LOG_DIR}"

LOG_FILE="${LOG_DIR}/ns3_batch_${RUN_TIMESTAMP}.log"
JSON_FILE="${LOG_DIR}/ns3_batch_${RUN_TIMESTAMP}.json"

# Redirect all output to both stdout and log file
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "Log file: ${LOG_FILE}"
echo "JSON summary: ${JSON_FILE}"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass_count=0
fail_count=0
warn_count=0

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
    echo ""
    echo "=============================================================================="
    echo " ${name}"
    echo "=============================================================================="
}

phase_end() {
    local name="$1"
    local status="$2"
    local elapsed=$(($(date +%s) - PHASE_START_TIME))
    PHASE_RESULTS+=("{\"phase\": \"${name}\", \"elapsed_seconds\": ${elapsed}, \"status\": \"${status}\"}")
    echo "  >> Phase elapsed: ${elapsed}s"
}

# ============================================================================
# Header
# ============================================================================
echo "=============================================================================="
echo " WSN Two-Layer Experiment - NS-3.35 Batch Runner"
echo "=============================================================================="
echo "Run timestamp : ${RUN_ISO}"
echo "NS-3 dir      : ${NS3_DIR}"
echo "Output dir    : ${OUTPUT_DIR}"
echo "Log file      : ${LOG_FILE}"
echo ""

declare -a PHASE_RESULTS

# Check NS-3 installation
if [ ! -f "${NS3_DIR}/ns3" ]; then
    echo -e "${RED}ERROR: NS-3.35 not found at ${NS3_DIR}${NC}"
    echo "Run setup_ns3.sh first to install NS-3.35"
    check_fail "NS-3.35 installation not found"
    exit 1
fi
check_pass "NS-3.35 installation found at ${NS3_DIR}"

# Clean previous output
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

cd "${NS3_DIR}"

# ------------------------------------------------------------------
# Phase 1: Full Experiment
# ------------------------------------------------------------------
phase_start "Phase 1: Full Experiment (4 scales x 6 protocols x 30 runs)"

PHASE1_START=$(date +%s)
./ns3 run scratch/wsn_two_layer_sim -- \
    --scales=100,200,300,500 \
    --runs=30 \
    --seed=42 \
    --output="${OUTPUT_DIR}"
PHASE1_EXIT=$?

if [ ${PHASE1_EXIT} -eq 0 ]; then
    check_pass "Full experiment completed"
    phase_end "Phase 1: Full Experiment" "PASS"
else
    check_fail "Full experiment failed with exit code ${PHASE1_EXIT}"
    phase_end "Phase 1: Full Experiment" "FAIL"
fi

# ------------------------------------------------------------------
# Phase 2: Ablation Study
# ------------------------------------------------------------------
phase_start "Phase 2: Ablation Study (300 nodes)"

PHASE2_START=$(date +%s)
./ns3 run scratch/wsn_two_layer_sim -- \
    --ablation \
    --runs=30 \
    --seed=42 \
    --output="${OUTPUT_DIR}"
PHASE2_EXIT=$?

if [ ${PHASE2_EXIT} -eq 0 ]; then
    check_pass "Ablation study completed"
    phase_end "Phase 2: Ablation Study" "PASS"
else
    check_fail "Ablation study failed with exit code ${PHASE2_EXIT}"
    phase_end "Phase 2: Ablation Study" "FAIL"
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
TOTAL_ELAPSED=$(($(date +%s) - START_TIME))

echo ""
echo "=============================================================================="
echo " Experiment Complete!"
echo "=============================================================================="
echo ""
echo "Output structure:"
echo "  ${OUTPUT_DIR}/"
echo "    scale_100/"
echo "      hnd_by_scale.csv"
echo "      energy_timeseries.csv"
echo "      jain_fairness.csv"
echo "    scale_200/"
echo "    scale_300/"
echo "    scale_500/"
echo "    ablation_study.csv"
echo ""
echo "Next: Use WSN-Figures to generate publication charts:"
echo "  cd ../../WSN-Figures/"
echo "  python src/run_pipeline.py --data-dir ${OUTPUT_DIR}"
echo ""

# Record run metadata
cat > "${OUTPUT_DIR}/run_metadata.json" << EOF
{
    "experiment": "WSN Two-Layer Optimization",
    "simulator": "NS-3.35",
    "hardware": "TelosB (MSP430 @ 8MHz, CC2420 radio)",
    "scales": [100, 200, 300, 500],
    "protocols": ["LEACH", "HEED", "PEGASIS", "DeepSensor", "FL-Energy", "Ours"],
    "runs_per_config": 30,
    "seed": 42,
    "ablation": true,
    "timestamp": "$(date -Iseconds)"
}
EOF

echo "Metadata saved to: ${OUTPUT_DIR}/run_metadata.json"
echo ""

# ------------------------------------------------------------------
# JSON Summary
# ------------------------------------------------------------------
cat > "${JSON_FILE}" << EOFJSON
{
    "script": "ns3_batch_run",
    "run_timestamp": "${RUN_ISO}",
    "ns3_dir": "${NS3_DIR}",
    "output_dir": "${OUTPUT_DIR}",
    "results": {
        "total_checks": $((pass_count + fail_count + warn_count)),
        "passed": ${pass_count},
        "failed": ${fail_count},
        "warnings": ${warn_count},
        "phase1_exit_code": ${PHASE1_EXIT},
        "phase2_exit_code": ${PHASE2_EXIT},
        "total_elapsed_seconds": ${TOTAL_ELAPSED}
    },
    "phases": [
        $(IFS=,; echo "${PHASE_RESULTS[*]}")
    ],
    "log_file": "${LOG_FILE}"
}
EOFJSON

echo ""
echo "=============================================================================="
echo " Run Summary"
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
    echo -e "${RED}EXPERIMENT FAILED - ${fail_count} check(s) failed.${NC}"
    echo "Review the log file for details:"
    echo "  cat ${LOG_FILE}"
    exit 1
fi

echo "=============================================================================="
echo " NS-3 Experiment Complete!"
echo "=============================================================================="