#!/bin/bash
# ============================================================================
# WSN Two-Layer Optimization - Unified Execution Script
# ============================================================================
# Runs the full pipeline: deploy → experiment → figures/tables
#
# Usage:
#   bash run_all.sh                        # Full pipeline
#   bash run_all.sh --skip-deploy           # Skip deploy, run experiment + pipeline
#   bash run_all.sh --skip-experiment       # Skip experiment, run deploy + pipeline
#   bash run_all.sh --skip-pipeline         # Skip pipeline, run deploy + experiment
#   bash run_all.sh --scales 100,200,300    # Custom scales
#   bash run_all.sh --runs 10               # Custom runs (quick test)
#   bash run_all.sh --ablation              # Ablation study only
#   bash run_all.sh --data-disk /mnt/data   # Custom data disk
#
# All logs are written to: logs/run_all_YYYYMMDD_HHMMSS/
#   master.log              - Master log (all phases)
#   master.json             - Master JSON summary
#   deploy/                 - Deploy phase logs
#   experiment/             - Experiment phase logs
#   pipeline/               - Pipeline phase logs
# ============================================================================

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_TIME=$(date +%s)
RUN_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
RUN_ISO=$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')

# ------------------------------------------------------------------
# Parse arguments
# ------------------------------------------------------------------
SKIP_DEPLOY=false
SKIP_EXPERIMENT=false
SKIP_PIPELINE=false
SCALES="100,200,300,500"
RUNS=30
SEED=42
ABLATION=false
DATA_DISK="/root/autodl-tmp"
PROTOCOLS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-deploy)     SKIP_DEPLOY=true; shift ;;
        --skip-experiment) SKIP_EXPERIMENT=true; shift ;;
        --skip-pipeline)   SKIP_PIPELINE=true; shift ;;
        --scales)          SCALES="$2"; shift 2 ;;
        --runs)            RUNS="$2"; shift 2 ;;
        --seed)            SEED="$2"; shift 2 ;;
        --ablation)        ABLATION=true; shift ;;
        --data-disk)       DATA_DISK="$2"; shift 2 ;;
        --protocols)       PROTOCOLS="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ------------------------------------------------------------------
# Logging setup - unified log directory
# ------------------------------------------------------------------
MASTER_LOG_DIR="${SCRIPT_DIR}/logs/run_all_${RUN_TIMESTAMP}"
mkdir -p "${MASTER_LOG_DIR}/deploy"
mkdir -p "${MASTER_LOG_DIR}/experiment"
mkdir -p "${MASTER_LOG_DIR}/pipeline"

MASTER_LOG="${MASTER_LOG_DIR}/master.log"
MASTER_JSON="${MASTER_LOG_DIR}/master.json"

# Redirect all output to both stdout and master log
exec > >(tee -a "${MASTER_LOG}") 2>&1

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Track phase results
PHASE_STATUSES=()
PHASE_ELAPSEDS=()

phase_start() {
    local name="$1"
    PHASE_START_TIME=$(date +%s)
    echo ""
    echo "##############################################################################"
    echo "# ${name}"
    echo "##############################################################################"
    echo "  Start: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
}

phase_end() {
    local name="$1"
    local status="$2"
    local elapsed=$(($(date +%s) - PHASE_START_TIME))
    PHASE_STATUSES+=("\"${name}\": \"${status}\"")
    PHASE_ELAPSEDS+=("\"${name}_elapsed\": ${elapsed}")
    echo ""
    echo "--- Phase complete: ${name} (${elapsed}s, ${status}) ---"
}

# ============================================================================
# Header
# ============================================================================
echo "##############################################################################"
echo "# WSN Two-Layer Optimization - Unified Execution Pipeline"
echo "##############################################################################"
echo "Run timestamp : ${RUN_ISO}"
echo "Script dir    : ${SCRIPT_DIR}"
echo "Master log    : ${MASTER_LOG}"
echo "Master JSON   : ${MASTER_JSON}"
echo ""
echo "Configuration:"
echo "  Scales       : ${SCALES}"
echo "  Runs         : ${RUNS}"
echo "  Seed         : ${SEED}"
echo "  Ablation     : ${ABLATION}"
echo "  Data disk    : ${DATA_DISK}"
echo "  Skip deploy  : ${SKIP_DEPLOY}"
echo "  Skip expr    : ${SKIP_EXPERIMENT}"
echo "  Skip pipeline: ${SKIP_PIPELINE}"
echo ""

# Record system info
HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
KERNEL=$(uname -r 2>/dev/null || echo "unknown")
ARCH=$(uname -m 2>/dev/null || echo "unknown")

# ============================================================================
# Phase 1: Deploy (Environment Verification)
# ============================================================================
if [ "${SKIP_DEPLOY}" = false ]; then
    phase_start "Phase 1: Environment Verification"

    DEPLOY_LOG="${MASTER_LOG_DIR}/deploy/deploy_${RUN_TIMESTAMP}.log"
    echo "  Deploy log: ${DEPLOY_LOG}"

    bash "${SCRIPT_DIR}/deploy.sh" \
        --data-disk "${DATA_DISK}" \
        --log-dir "${MASTER_LOG_DIR}/deploy" \
        > "${DEPLOY_LOG}" 2>&1
    DEPLOY_EXIT=$?

    if [ ${DEPLOY_EXIT} -eq 0 ]; then
        echo -e "  ${GREEN}Environment verification PASSED${NC}"
        phase_end "Phase 1: Environment Verification" "PASS"
    else
        echo -e "  ${RED}Environment verification FAILED (exit=${DEPLOY_EXIT})${NC}"
        echo "  Review deploy log: cat ${DEPLOY_LOG}"
        phase_end "Phase 1: Environment Verification" "FAIL"
        # Don't abort - environment may still be usable for experiments
    fi
else
    echo -e "  ${YELLOW}Phase 1: Environment Verification - SKIPPED${NC}"
    PHASE_STATUSES+=('"Phase 1: Environment Verification": "SKIP"')
    PHASE_ELAPSEDS+=('"Phase 1: Environment Verification_elapsed": 0')
fi

# ============================================================================
# Phase 2: Experiment
# ============================================================================
if [ "${SKIP_EXPERIMENT}" = false ]; then
    phase_start "Phase 2: Experiment Execution"

    PYTHON_BIN=$(which python3 || which python || echo "")
    if [ -z "${PYTHON_BIN}" ]; then
        echo -e "  ${RED}Python not found. Cannot run experiments.${NC}"
        phase_end "Phase 2: Experiment Execution" "FAIL"
        exit 1
    fi
    RUNNER="${SCRIPT_DIR}/WSN-Experiment/run_experiment.py"
    EXPERIMENT_LOG="${MASTER_LOG_DIR}/experiment/experiment_${RUN_TIMESTAMP}.log"

    echo "  Python: ${PYTHON_BIN}"
    echo "  Runner: ${RUNNER}"
    echo "  Experiment log: ${EXPERIMENT_LOG}"

    CMD=(
        "${PYTHON_BIN}" "${RUNNER}"
        --scales "${SCALES}"
        --runs "${RUNS}"
        --seed "${SEED}"
        --output "${SCRIPT_DIR}/WSN-Experiment/output"
    )

    if [ -n "${PROTOCOLS}" ]; then
        CMD+=(--protocols "${PROTOCOLS}")
    fi
    if [ "${ABLATION}" = true ]; then
        CMD+=(--ablation)
    fi

    echo "  Command: ${CMD[*]}"
    echo ""

    "${CMD[@]}" > "${EXPERIMENT_LOG}" 2>&1
    EXPERIMENT_EXIT=$?

    if [ ${EXPERIMENT_EXIT} -eq 0 ]; then
        echo -e "  ${GREEN}Experiment execution PASSED${NC}"
        phase_end "Phase 2: Experiment Execution" "PASS"
    else
        echo -e "  ${RED}Experiment execution FAILED (exit=${EXPERIMENT_EXIT})${NC}"
        echo "  Review experiment log: cat ${EXPERIMENT_LOG}"
        echo "  Last 20 lines:"
        tail -20 "${EXPERIMENT_LOG}" | sed 's/^/    /'
        phase_end "Phase 2: Experiment Execution" "FAIL"
    fi
else
    echo -e "  ${YELLOW}Phase 2: Experiment Execution - SKIPPED${NC}"
    PHASE_STATUSES+=('"Phase 2: Experiment Execution": "SKIP"')
    PHASE_ELAPSEDS+=('"Phase 2: Experiment Execution_elapsed": 0')
fi

# ============================================================================
# Phase 3: Figures & Tables Pipeline
# ============================================================================
if [ "${SKIP_PIPELINE}" = false ]; then
    phase_start "Phase 3: Figures & Tables Generation"

    PYTHON_BIN=$(which python3 || which python || echo "")
    if [ -z "${PYTHON_BIN}" ]; then
        echo -e "  ${RED}Python not found. Cannot generate figures/tables.${NC}"
        phase_end "Phase 3: Figures & Tables Generation" "FAIL"
        exit 1
    fi
    PIPELINE="${SCRIPT_DIR}/WSN-Figures/src/run_pipeline.py"
    PIPELINE_LOG="${MASTER_LOG_DIR}/pipeline/pipeline_${RUN_TIMESTAMP}.log"

    echo "  Python: ${PYTHON_BIN}"
    echo "  Pipeline: ${PIPELINE}"
    echo "  Pipeline log: ${PIPELINE_LOG}"

    "${PYTHON_BIN}" "${PIPELINE}" \
        --data-dir "${SCRIPT_DIR}/WSN-Experiment/output" \
        > "${PIPELINE_LOG}" 2>&1
    PIPELINE_EXIT=$?

    if [ ${PIPELINE_EXIT} -eq 0 ]; then
        echo -e "  ${GREEN}Figures & tables generation PASSED${NC}"
        phase_end "Phase 3: Figures & Tables Generation" "PASS"
    else
        echo -e "  ${RED}Figures & tables generation FAILED (exit=${PIPELINE_EXIT})${NC}"
        echo "  Review pipeline log: cat ${PIPELINE_LOG}"
        echo "  Last 20 lines:"
        tail -20 "${PIPELINE_LOG}" | sed 's/^/    /'
        phase_end "Phase 3: Figures & Tables Generation" "FAIL"
    fi
else
    echo -e "  ${YELLOW}Phase 3: Figures & Tables Generation - SKIPPED${NC}"
    PHASE_STATUSES+=('"Phase 3: Figures & Tables Generation": "SKIP"')
    PHASE_ELAPSEDS+=('"Phase 3: Figures & Tables Generation_elapsed": 0')
fi

# ============================================================================
# Master JSON Summary
# ============================================================================
TOTAL_ELAPSED=$(($(date +%s) - START_TIME))

cat > "${MASTER_JSON}" << EOFJSON
{
    "pipeline": "run_all",
    "run_timestamp": "${RUN_ISO}",
    "hostname": "${HOSTNAME}",
    "os": {
        "kernel": "${KERNEL}",
        "arch": "${ARCH}"
    },
    "configuration": {
        "scales": "${SCALES}",
        "runs": ${RUNS},
        "seed": ${SEED},
        "ablation": ${ABLATION},
        "protocols": "${PROTOCOLS:-all}",
        "data_disk": "${DATA_DISK}"
    },
    "phases": {
        $(IFS=,; echo "${PHASE_STATUSES[*]}")
    },
    "timing": {
        $(IFS=,; echo "${PHASE_ELAPSEDS[*]}"),
        "total_elapsed_seconds": ${TOTAL_ELAPSED}
    },
    "logs": {
        "master_log": "${MASTER_LOG}",
        "master_json": "${MASTER_JSON}",
        "deploy_dir": "${MASTER_LOG_DIR}/deploy/",
        "experiment_dir": "${MASTER_LOG_DIR}/experiment/",
        "pipeline_dir": "${MASTER_LOG_DIR}/pipeline/"
    },
    "outputs": {
        "experiment_data": "${SCRIPT_DIR}/WSN-Experiment/output/",
        "figures": "${SCRIPT_DIR}/WSN-Figures/output/figures/",
        "tables": "${SCRIPT_DIR}/WSN-Figures/output/tables/",
        "statistical_report": "${SCRIPT_DIR}/WSN-Figures/output/statistical_report.txt"
    }
}
EOFJSON

# ============================================================================
# Final Summary
# ============================================================================
echo ""
echo "##############################################################################"
echo "# Pipeline Complete"
echo "##############################################################################"
echo ""
echo "  Total elapsed: ${TOTAL_ELAPSED}s"
echo ""
echo "  Log directory:"
echo "    Master log   : ${MASTER_LOG}"
echo "    Master JSON  : ${MASTER_JSON}"
echo "    Deploy logs  : ${MASTER_LOG_DIR}/deploy/"
echo "    Experiment   : ${MASTER_LOG_DIR}/experiment/"
echo "    Pipeline     : ${MASTER_LOG_DIR}/pipeline/"
echo ""
echo "  Outputs:"
echo "    Experiment data: ${SCRIPT_DIR}/WSN-Experiment/output/"
echo "    Figures        : ${SCRIPT_DIR}/WSN-Figures/output/figures/"
echo "    Tables         : ${SCRIPT_DIR}/WSN-Figures/output/tables/"
echo "    Stats report   : ${SCRIPT_DIR}/WSN-Figures/output/statistical_report.txt"
echo ""
echo "  Quick log analysis:"
echo "    python3 WSN-Experiment/scripts/analyze_logs.py WSN-Experiment/output/logs/"
echo "    python3 WSN-Experiment/scripts/analyze_logs.py WSN-Figures/output/logs/"
echo ""

# Check if any phase failed
FAILED=0
for status in "${PHASE_STATUSES[@]}"; do
    if echo "$status" | grep -q '"FAIL"'; then
        FAILED=1
    fi
done

if [ ${FAILED} -eq 1 ]; then
    echo -e "${RED}PIPELINE COMPLETED WITH FAILURES - review master log:${NC}"
    echo "  cat ${MASTER_LOG}"
    exit 1
fi

echo "##############################################################################"
echo "# All phases completed successfully!"
echo "##############################################################################"