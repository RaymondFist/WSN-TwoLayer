#!/usr/bin/env python3
"""
Verify that the scale_500 fix is correct.
Runs all protocols for scale_500 with 3 runs to verify the fix.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_experiment import (
    SimConfig, TwoLayerOrchestrator,
    LeachBaseline, HeedBaseline, PegasisBaseline, DrlBaseline, FlEnergyBaseline,
)

def run_verification():
    print("=" * 70)
    print("Scale 500 Fix Verification")
    print("=" * 70)
    
    config = SimConfig(
        num_nodes=500,
        max_iterations=300,
        num_runs=3,
        random_seed=42,
    )
    
    protocols = [
        ("LEACH", LeachBaseline),
        ("HEED", HeedBaseline),
        ("PEGASIS", PegasisBaseline),
        ("DeepSensor", DrlBaseline),
        ("FL-Energy", FlEnergyBaseline),
    ]
    
    print(f"\nConfiguration:")
    print(f"  Scale: {config.num_nodes} nodes")
    print(f"  Max iterations: {config.max_iterations}")
    print(f"  Runs: {config.num_runs}")
    print()
    
    for name, cls in protocols:
        print(f"  Running {name}...")
        total_hnd = 0.0
        total_jain = 0.0
        valid_runs = 0
        
        for run in range(config.num_runs):
            config.random_seed = 42 + run
            protocol = cls(config)
            protocol.initialize()
            for r in range(config.max_iterations):
                if not protocol.step(r):
                    break
            result = protocol.get_result()
            hnd = result.hnd_mean
            jain = result.jains_fairness
            total_hnd += hnd
            total_jain += jain
            valid_runs += 1
            print(f"    Run {run+1}: HND={hnd:.2f}, Jain={jain:.4f}")
        
        avg_hnd = total_hnd / valid_runs
        avg_jain = total_jain / valid_runs
        print(f"  {name}: Average HND={avg_hnd:.2f}, Average Jain={avg_jain:.4f}")
        print()

if __name__ == "__main__":
    run_verification()
