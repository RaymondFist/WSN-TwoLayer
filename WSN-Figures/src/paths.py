"""
Centralized path management for wsn-figures project.

Reads raw experiment data from wsn-experiment/output/ and
writes figures/tables to wsn-figures/output/.
"""
import os
from pathlib import Path

# Project roots
PROJECT_ROOT = Path(__file__).parent.parent
EXPERIMENT_ROOT = PROJECT_ROOT.parent / 'WSN-Experiment'

def figures_dir():
    """Output directory for generated figures."""
    d = PROJECT_ROOT / 'output' / 'figures'
    d.mkdir(parents=True, exist_ok=True)
    return d

def tables_dir():
    """Output directory for generated tables."""
    d = PROJECT_ROOT / 'output' / 'tables'
    d.mkdir(parents=True, exist_ok=True)
    return d

def config_dir():
    """Configuration directory."""
    d = PROJECT_ROOT / 'config'
    d.mkdir(parents=True, exist_ok=True)
    return d

def experiment_data_dir(scale=None):
    """
    Directory containing raw experiment data.
    Reads from wsn-experiment/output/scale_{N}/ by default.
    """
    base = EXPERIMENT_ROOT / 'output'
    if scale is not None:
        base = base / f'scale_{scale}'
    return base

def experiment_output_dir():
    """Default experiment output directory."""
    d = EXPERIMENT_ROOT / 'output'
    return d

def figure_path(name):
    """Get full path for a figure file."""
    return figures_dir() / name

def table_path(name):
    """Get full path for a table file."""
    return tables_dir() / name