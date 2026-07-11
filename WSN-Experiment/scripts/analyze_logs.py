#!/usr/bin/env python3
"""
Analyze experiment execution logs (JSON summaries).

Quickly checks whether experiments ran correctly by parsing the JSON
summary files produced by run_experiment.py.

Usage:
    python scripts/analyze_logs.py output/logs/
    python scripts/analyze_logs.py output/logs/ --detail
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime


def analyze_logs(log_dir: str, detail: bool = False):
    log_dir = Path(log_dir)
    if not log_dir.exists():
        print(f"ERROR: Log directory not found: {log_dir}")
        sys.exit(1)

    json_files = sorted(log_dir.glob("*.json"))
    if not json_files:
        print(f"WARNING: No JSON log files found in {log_dir}")
        sys.exit(1)

    print("=" * 65)
    print(" WSN Experiment Log Analysis")
    print("=" * 65)
    print(f" Log directory: {log_dir}")
    print(f" JSON files found: {len(json_files)}")
    print()

    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)

        script = data.get("script", "unknown")
        start = data.get("start_time", "unknown")
        end = data.get("end_time", "unknown")
        elapsed = data.get("total_elapsed_seconds", 0)
        exit_code = data.get("exit_code", -1)
        errors = data.get("error_count", 0)
        warnings = data.get("warning_count", 0)

        status = "PASS" if exit_code == 0 and errors == 0 else "FAIL"
        if exit_code == 0 and errors == 0 and warnings > 0:
            status = "WARN"

        status_mark = {"PASS": "[OK] ", "FAIL": "[FAIL]", "WARN": "[WARN]"}.get(status, "[???]")

        print(f"{status_mark} {script}")
        print(f"   File      : {jf.name}")
        print(f"   Start     : {start}")
        print(f"   End       : {end}")
        print(f"   Elapsed   : {elapsed:.1f}s")
        print(f"   Exit code : {exit_code}")
        print(f"   Errors    : {errors}")
        print(f"   Warnings  : {warnings}")

        # Phases
        phases = data.get("phases", [])
        if phases:
            print(f"   Phases    : {len(phases)}")
            for p in phases:
                p_status = {"PASS": "OK", "FAIL": "FAIL", "WARN": "WARN", "SKIP": "SKIP"}.get(
                    p.get("status", ""), p.get("status", "?"))
                print(f"     [{p_status}] {p['phase']} ({p.get('elapsed_seconds', 0):.1f}s)")

        # Protocol results
        protocol_results = data.get("protocol_results", [])
        if protocol_results and detail:
            print(f"   Protocols  : {len(protocol_results)}")
            for pr in protocol_results:
                proto = pr.get("protocol", "?")
                scale = pr.get("scale", "?")
                elapsed_s = pr.get("elapsed_s", 0)
                print(f"     {proto} (scale={scale}): {elapsed_s:.1f}s")

        # Figures
        figures = data.get("figures", [])
        if figures:
            print(f"   Figures    : {len(figures)}")
            for fig in figures:
                f_status = fig.get("status", "?")
                f_status_mark = {"OK": "OK", "FAIL": "FAIL", "SKIP": "SKIP"}.get(f_status, f_status)
                print(f"     [{f_status_mark}] {fig['name']} -> {fig.get('output', '?')}")

        # Tables
        tables = data.get("tables", [])
        if tables:
            print(f"   Tables     : {len(tables)}")
            for tab in tables:
                t_status = tab.get("status", "?")
                t_status_mark = {"OK": "OK", "FAIL": "FAIL", "SKIP": "SKIP"}.get(t_status, t_status)
                print(f"     [{t_status_mark}] {tab['name']} -> {tab.get('output', '?')}")

        # Data loaded
        data_loaded = data.get("data_loaded", {})
        if data_loaded and detail:
            print(f"   Data loaded:")
            for name, info in data_loaded.items():
                print(f"     {name}: {info.get('rows', 0)} rows")

        # Errors detail
        if errors > 0 and detail:
            print(f"   Error details:")
            for e in data.get("errors", []):
                print(f"     [{e.get('time', '?')}] {e.get('message', '?')}")

        print()

    # Overall summary
    total_errors = 0
    total_warnings = 0
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
        total_errors += data.get("error_count", 0)
        total_warnings += data.get("warning_count", 0)

    print("=" * 65)
    if total_errors == 0 and total_warnings == 0:
        print(" ALL CLEAN - No errors or warnings detected.")
    elif total_errors == 0:
        print(f" WARNINGS ONLY - {total_warnings} warning(s), no errors.")
    else:
        print(f" ISSUES FOUND - {total_errors} error(s), {total_warnings} warning(s).")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Analyze WSN experiment logs")
    parser.add_argument("log_dir", help="Path to log directory")
    parser.add_argument("--detail", action="store_true", help="Show detailed output")
    args = parser.parse_args()
    analyze_logs(args.log_dir, args.detail)


if __name__ == "__main__":
    main()