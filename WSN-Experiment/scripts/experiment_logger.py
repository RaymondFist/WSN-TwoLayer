"""
Shared logging utility for WSN-Experiment scripts.

Provides dual output (console + timestamped log file) and a JSON summary
file for machine-readable post-run analysis.

Usage:
    from scripts.experiment_logger import ExperimentLogger

    logger = ExperimentLogger("output/logs", "run_experiment")
    logger.info("Starting experiment...")
    logger.log_phase("Scale 300", elapsed_s=45.2, status="PASS")
    logger.log_protocol_result("Ours", 300, {"HND": 1234.5, "DR": 0.95})
    logger.finalize(exit_code=0)
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


class ExperimentLogger:
    """Dual-output logger with JSON summary for experiment scripts."""

    def __init__(self, log_dir: str, script_name: str):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.script_name = script_name
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()

        # File paths
        self.log_file = self.log_dir / f"{script_name}_{self.timestamp}.log"
        self.json_file = self.log_dir / f"{script_name}_{self.timestamp}.json"

        # Setup Python logging
        self._logger = logging.getLogger(f"{script_name}_{self.timestamp}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()

        # File handler - detailed
        fh = logging.FileHandler(str(self.log_file), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        self._logger.addHandler(fh)

        # Console handler - info and above
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(ch)

        # JSON summary data
        self._json = {
            "script": script_name,
            "start_time": self.start_time.isoformat(),
            "phases": [],
            "protocol_results": [],
            "errors": [],
            "warnings": [],
        }

        # Log header
        self._logger.info("=" * 65)
        self._logger.info(f" {script_name} - Execution Log")
        self._logger.info("=" * 65)
        self._logger.info(f" Start time : {self.start_time.isoformat()}")
        self._logger.info(f" Log file   : {self.log_file}")
        self._logger.info(f" JSON file  : {self.json_file}")
        self._logger.info("")

    def _record(self, level: str, msg: str):
        """Record to both log and JSON summary for errors/warnings."""
        if level == "ERROR":
            self._json["errors"].append({
                "time": datetime.now().isoformat(),
                "message": msg,
            })
        elif level == "WARNING":
            self._json["warnings"].append({
                "time": datetime.now().isoformat(),
                "message": msg,
            })

    def debug(self, msg: str):
        self._logger.debug(msg)

    def info(self, msg: str):
        self._logger.info(msg)

    def warning(self, msg: str):
        self._logger.warning(f"WARNING: {msg}")
        self._record("WARNING", msg)

    def error(self, msg: str):
        self._logger.error(f"ERROR: {msg}")
        self._record("ERROR", msg)

    def log_section(self, title: str):
        """Log a section header."""
        self._logger.info("")
        self._logger.info("-" * 50)
        self._logger.info(f" {title}")
        self._logger.info("-" * 50)

    def log_phase(self, name: str, elapsed_s: float, status: str = "PASS",
                  details: Optional[Dict] = None):
        """Log a completed phase with timing and status."""
        entry = {
            "phase": name,
            "elapsed_seconds": round(elapsed_s, 2),
            "status": status,
        }
        if details:
            entry["details"] = details
        self._json["phases"].append(entry)

        status_mark = {"PASS": "OK", "FAIL": "FAIL", "WARN": "WARN"}.get(status, status)
        self._logger.info(f"  [{status_mark}] {name} ({elapsed_s:.1f}s)")

    def log_protocol_result(self, protocol: str, scale: int, metrics: Dict):
        """Log a protocol result for JSON summary."""
        entry = {
            "protocol": protocol,
            "scale": scale,
            **metrics,
        }
        self._json["protocol_results"].append(entry)

    def log_config(self, config: Dict):
        """Log experiment configuration."""
        self._json["config"] = config
        self._logger.info("--- Configuration ---")
        for key, value in config.items():
            if isinstance(value, list):
                self._logger.info(f"  {key}: {value}")
            else:
                self._logger.info(f"  {key}: {value}")
        self._logger.info("")

    def finalize(self, exit_code: int = 0):
        """Write JSON summary and log footer."""
        end_time = datetime.now()
        elapsed = (end_time - self.start_time).total_seconds()

        self._json["end_time"] = end_time.isoformat()
        self._json["total_elapsed_seconds"] = round(elapsed, 2)
        self._json["exit_code"] = exit_code
        self._json["error_count"] = len(self._json["errors"])
        self._json["warning_count"] = len(self._json["warnings"])

        # Write JSON
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(self._json, f, indent=2, ensure_ascii=False)

        self._logger.info("")
        self._logger.info("=" * 65)
        self._logger.info(f" Execution complete")
        self._logger.info(f" End time    : {end_time.isoformat()}")
        self._logger.info(f" Elapsed     : {elapsed:.1f}s")
        self._logger.info(f" Exit code   : {exit_code}")
        self._logger.info(f" Errors      : {len(self._json['errors'])}")
        self._logger.info(f" Warnings    : {len(self._json['warnings'])}")
        self._logger.info(f" JSON summary: {self.json_file}")
        self._logger.info("=" * 65)