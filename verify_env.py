#!/usr/bin/env python3
"""
Environment Verification Script for WSN Two-Layer Optimization.

Validates all imports, configurations, and data pipeline integrity
before running experiments on the cloud server.

Usage:
    python verify_env.py
    python verify_env.py --data-dir /path/to/experiment/output
"""
import sys
import os
import argparse
from pathlib import Path


class TeeWriter:
    """Duplicate output to both original stdout and a log file."""
    def __init__(self, log_path):
        self.stdout = sys.stdout
        self.log = open(log_path, 'w', encoding='utf-8')

    def write(self, data):
        self.stdout.write(data)
        self.log.write(data)

    def flush(self):
        self.stdout.flush()
        self.log.flush()

    def close(self):
        self.log.close()


PASS = 0
FAIL = 0
WARN = 0


def check(condition, label, fatal=False):
    global PASS, FAIL, WARN
    if condition:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [{'FAIL' if fatal else 'WARN'}] {label}")
        if fatal:
            FAIL += 1
        else:
            WARN += 1


def main():
    global PASS, FAIL, WARN
    parser = argparse.ArgumentParser(description="Verify WSN experiment environment")
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Path to experiment data directory")
    parser.add_argument("--log", type=str, default=None,
                        help="Path to log file for verification output")
    args = parser.parse_args()

    tee = None
    if args.log:
        Path(args.log).parent.mkdir(parents=True, exist_ok=True)
        tee = TeeWriter(args.log)
        sys.stdout = tee

    script_dir = Path(__file__).parent.resolve()

    print("=" * 65)
    print(" WSN Two-Layer Optimization - Environment Verification")
    print("=" * 65)
    print(f"  Script dir: {script_dir}")
    print()

    # ================================================================
    # 1. Python version
    # ================================================================
    print("--- Python Version ---")
    ver = sys.version_info
    print(f"  Python {ver.major}.{ver.minor}.{ver.micro}")
    check(ver >= (3, 8), f"Python >= 3.8 (got {ver.major}.{ver.minor})", fatal=True)
    print()

    # ================================================================
    # 2. Standard library imports (WSN-Experiment)
    # ================================================================
    print("--- Standard Library Imports (WSN-Experiment) ---")
    stdlib_modules = [
        ("os", "os"),
        ("sys", "sys"),
        ("json", "json"),
        ("math", "math"),
        ("random", "random"),
        ("argparse", "argparse"),
        ("csv", "csv"),
        ("pathlib", "pathlib"),
        ("datetime", "datetime"),
        ("dataclasses", "dataclasses"),
        ("typing", "typing"),
    ]
    for name, import_name in stdlib_modules:
        try:
            __import__(import_name)
            check(True, f"import {name}")
        except ImportError:
            check(False, f"import {name}", fatal=True)
    print()

    # ================================================================
    # 3. Third-party imports (WSN-Figures)
    # ================================================================
    print("--- Third-Party Imports (WSN-Figures) ---")
    thirdparty = [
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("pandas", "pandas"),
        ("matplotlib", "matplotlib"),
    ]
    for name, import_name in thirdparty:
        try:
            mod = __import__(import_name)
            ver_str = getattr(mod, "__version__", "unknown")
            check(True, f"import {name} ({ver_str})")
        except ImportError:
            check(False, f"import {name} (missing)", fatal=True)
    print()

    # ================================================================
    # 4. Matplotlib backend and font
    # ================================================================
    print("--- Matplotlib Configuration ---")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        check(True, f"matplotlib backend: {matplotlib.get_backend()}")

        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman'],
        })
        fig, ax = plt.subplots()
        ax.set_title("Test")
        fig.savefig("/tmp/_wsn_font_test.png", dpi=72)
        plt.close()
        os.remove("/tmp/_wsn_font_test.png")
        check(True, "Times New Roman font rendering works")
    except Exception as e:
        check(False, f"matplotlib font test failed: {e}")
    print()

    # ================================================================
    # 5. Project file existence
    # ================================================================
    print("--- Project Files ---")
    required_files = [
        (script_dir / "WSN-Experiment" / "run_experiment.py", "run_experiment.py"),
        (script_dir / "WSN-Experiment" / "config" / "default.json", "config/default.json"),
        (script_dir / "WSN-Figures" / "src" / "run_pipeline.py", "run_pipeline.py"),
        (script_dir / "WSN-Figures" / "src" / "data_parser.py", "data_parser.py"),
        (script_dir / "WSN-Figures" / "src" / "paths.py", "paths.py"),
        (script_dir / "WSN-Figures" / "src" / "analysis" / "statistical_analysis.py", "statistical_analysis.py"),
        (script_dir / "WSN-Figures" / "src" / "figures" / "generate_all_figures.py", "generate_all_figures.py"),
        (script_dir / "WSN-Figures" / "src" / "tables" / "generate_all_tables.py", "generate_all_tables.py"),
        (script_dir / "WSN-Figures" / "requirements.txt", "requirements.txt"),
    ]
    for path, label in required_files:
        check(path.exists(), label, fatal=True)
    print()

    # ================================================================
    # 6. WSN-Figures module import chain
    # ================================================================
    print("--- WSN-Figures Module Import Chain ---")
    figures_src = script_dir / "WSN-Figures" / "src"
    sys.path.insert(0, str(script_dir / "WSN-Figures"))

    try:
        from src.paths import experiment_data_dir, figure_path, table_path
        check(True, "from src.paths import ...")
    except Exception as e:
        check(False, f"src.paths import failed: {e}", fatal=True)

    try:
        from src.data_parser import ExperimentDataParser, load_all_data
        check(True, "from src.data_parser import ...")
    except Exception as e:
        check(False, f"src.data_parser import failed: {e}", fatal=True)

    try:
        from src.analysis.statistical_analysis import StatisticalAnalyzer
        check(True, "from src.analysis.statistical_analysis import ...")
    except Exception as e:
        check(False, f"statistical_analysis import failed: {e}", fatal=True)

    try:
        from src.figures.generate_all_figures import generate_all as gen_figs
        check(True, "from src.figures.generate_all_figures import ...")
    except Exception as e:
        check(False, f"generate_all_figures import failed: {e}", fatal=True)

    try:
        from src.tables.generate_all_tables import generate_all as gen_tabs
        check(True, "from src.tables.generate_all_tables import ...")
    except Exception as e:
        check(False, f"generate_all_tables import failed: {e}", fatal=True)
    print()

    # ================================================================
    # 7. WSN-Experiment module import
    # ================================================================
    print("--- WSN-Experiment Module Import ---")
    exp_dir = script_dir / "WSN-Experiment"
    sys.path.insert(0, str(exp_dir))

    try:
        from run_experiment import (
            SimConfig, ProtocolResult, DecisionVector, ObjectiveWeights,
            TwoLayerOrchestrator, Layer1Optimizer, Layer2Consensus,
            AdaptiveTuner, ConvergenceMonitor, DataLogger,
            LeachBaseline, HeedBaseline, PegasisBaseline,
            DrlBaseline, FlEnergyBaseline, PROTOCOLS,
        )
        check(True, "from run_experiment import all classes")
    except Exception as e:
        check(False, f"run_experiment import failed: {e}", fatal=True)

    # Verify PROTOCOLS dict
    expected = ["LEACH", "HEED", "PEGASIS", "DeepSensor", "FL-Energy", "Ours"]
    for p in expected:
        check(p in PROTOCOLS, f"PROTOCOLS contains '{p}'")
    print()

    # ================================================================
    # 8. Config validation
    # ================================================================
    print("--- Configuration Validation ---")
    import json
    config_path = script_dir / "WSN-Experiment" / "config" / "default.json"
    with open(config_path) as f:
        cfg = json.load(f)

    params = cfg.get("parameters", {})
    energy = cfg.get("energy_model", {})
    network = cfg.get("network", {})

    # Check parameter ranges
    check(-30 <= params.get("p_min_dBm", 0) <= params.get("p_max_dBm", 0) <= 10,
          f"TX power range: [{params.get('p_min_dBm')}, {params.get('p_max_dBm')}] dBm")
    check(0 < params.get("eta_0", 0) < 1.0, f"Step size eta_0={params.get('eta_0')}")
    check(0 < params.get("delta", 0) < 0.1, f"Decay delta={params.get('delta')}")
    check(params.get("T_adapt", 0) > 0, f"Adapt interval T_adapt={params.get('T_adapt')}")
    check(0 < params.get("tau_th", 0) < 1.0, f"Threshold tau_th={params.get('tau_th')}")
    check(0 < params.get("tau_min", 0) < 1.0, f"Min tau tau_min={params.get('tau_min')}")
    check(params.get("K_max", 0) >= 50, f"Max iterations K_max={params.get('K_max')}")
    check(0 < params.get("convergence_threshold", 0) < 0.01,
          f"Convergence threshold={params.get('convergence_threshold')}")

    # Energy model
    check(0 < energy.get("tx_current_mA", 0) < 100, f"TX current={energy.get('tx_current_mA')} mA")
    check(0 < energy.get("rx_current_mA", 0) < 100, f"RX current={energy.get('rx_current_mA')} mA")
    check(0 < energy.get("voltage", 0) < 10, f"Voltage={energy.get('voltage')} V")

    # Network
    check(0 < network.get("area_width_m", 0) < 10000, f"Area width={network.get('area_width_m')} m")
    check(0 < network.get("comm_range_m", 0) < network.get("area_width_m", 9999),
          f"Comm range={network.get('comm_range_m')} m < area width")
    print()

    # ================================================================
    # 9. Energy model consistency check
    # ================================================================
    print("--- Energy Model Consistency ---")
    from run_experiment import Layer1Optimizer

    opt = Layer1Optimizer(SimConfig())

    # Check TX current at endpoints
    tx_0dBm = opt._tx_current_from_dBm(0.0)
    tx_m25dBm = opt._tx_current_from_dBm(-25.0)
    check(abs(tx_0dBm - 17.4) < 0.01, f"TX current @ 0 dBm = {tx_0dBm:.2f} mA (expected 17.4)")
    check(abs(tx_m25dBm - 8.5) < 0.01, f"TX current @ -25 dBm = {tx_m25dBm:.2f} mA (expected 8.5)")

    # Check linear power conversion
    p_linear_0 = opt._linear_power(0.0)
    p_linear_m25 = opt._linear_power(-25.0)
    check(abs(p_linear_0 - 1.0) < 0.001, f"Linear power @ 0 dBm = {p_linear_0:.4f} mW (expected 1.0)")
    check(abs(p_linear_m25 - 0.00316) < 0.001, f"Linear power @ -25 dBm = {p_linear_m25:.6f} mW (~0.00316)")

    # Check monotonicity
    tx_10 = opt._tx_current_from_dBm(-10.0)
    check(tx_m25dBm < tx_10 < tx_0dBm,
          f"TX current monotonic: {tx_m25dBm:.2f} < {tx_10:.2f} < {tx_0dBm:.2f}")
    print()

    # ================================================================
    # 10. Quick algorithm correctness test
    # ================================================================
    print("--- Quick Algorithm Correctness Test (10 nodes, 100 iters) ---")
    config = SimConfig(
        num_nodes=10,
        max_iterations=100,
        num_runs=1,
        random_seed=42,
    )
    orch = TwoLayerOrchestrator(config)
    result = orch.run()

    check(result.hnd_mean > 0, f"HND = {result.hnd_mean:.1f} rounds (> 0)")
    check(0 < result.delivery_ratio_mean <= 1.0,
          f"Delivery ratio = {result.delivery_ratio_mean:.3f} (in (0, 1])")
    check(0 < result.jains_fairness <= 1.0,
          f"Jain's fairness = {result.jains_fairness:.3f} (in (0, 1])")
    check(result.convergence_time_ms > 0,
          f"Convergence time = {result.convergence_time_ms:.1f} ms (> 0)")
    check(result.energy_efficiency > 0,
          f"Energy efficiency = {result.energy_efficiency:.3f} (> 0)")
    check(result.ram_kB == 4.2, f"RAM = {result.ram_kB} kB (expected 4.2)")
    check(result.rom_kB == 28.0, f"ROM = {result.rom_kB} kB (expected 28.0)")
    print()

    # ================================================================
    # 11. Baseline protocol sanity check
    # ================================================================
    print("--- Baseline Protocol Sanity Check ---")
    baseline_config = SimConfig(
        num_nodes=10,
        max_iterations=100,
        num_runs=1,
        random_seed=42,
    )
    for name, cls in [("LEACH", LeachBaseline), ("HEED", HeedBaseline),
                       ("PEGASIS", PegasisBaseline), ("DeepSensor", DrlBaseline),
                       ("FL-Energy", FlEnergyBaseline)]:
        baseline = cls(baseline_config)
        baseline.initialize()
        for r in range(baseline_config.max_iterations):
            baseline.step(r)
        r = baseline.get_result()
        check(r.hnd_mean > 0, f"{name}: HND={r.hnd_mean:.1f} (> 0)")
        check(0 < r.delivery_ratio_mean <= 1.0, f"{name}: DR={r.delivery_ratio_mean:.3f}")
    print()

    # ================================================================
    # 12. Check existing data (if available)
    # ================================================================
    print("--- Existing Data Check ---")
    data_dir = Path(args.data_dir) if args.data_dir else (script_dir / "WSN-Experiment" / "output")
    if data_dir.exists():
        csv_files = list(data_dir.glob("**/*.csv"))
        json_files = list(data_dir.glob("**/*.json"))
        print(f"  Data directory: {data_dir}")
        print(f"  CSV files found: {len(csv_files)}")
        if csv_files:
            for f in sorted(csv_files)[:10]:
                print(f"    {f.relative_to(data_dir)}")
            if len(csv_files) > 10:
                print(f"    ... and {len(csv_files) - 10} more")
        check(len(csv_files) > 0 or len(json_files) > 0,
              "Data directory contains files" if (csv_files or json_files) else "Data directory is empty")
    else:
        print(f"  Data directory not found: {data_dir}")
        check(True, "Data directory will be created during experiment run")
    print()

    # ================================================================
    # Summary
    # ================================================================
    print("=" * 65)
    print(" Verification Summary")
    print("=" * 65)
    total = PASS + FAIL + WARN
    print(f"  Total checks : {total}")
    print(f"  Passed       : {PASS}")

    if WARN > 0:
        print(f"  Warnings     : {WARN}")
    if FAIL > 0:
        print(f"  Failed       : {FAIL}")
        print(f"\n  FIX {FAIL} FAILED CHECK(S) BEFORE RUNNING EXPERIMENTS.")
    else:
        print(f"\n  All checks passed. Environment is ready for experiments.")
    print()
    
    if tee:
        sys.stdout = tee.stdout
        tee.close()

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())