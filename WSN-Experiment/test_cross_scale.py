"""Cross-scale validation: all protocols at all scales."""
import sys
sys.path.insert(0, '.')
from run_experiment import (
    LeachBaseline, HeedBaseline, PegasisBaseline,
    DrlBaseline, FlEnergyBaseline, TwoLayerOrchestrator, SimConfig
)

protocols = {
    'LEACH': LeachBaseline,
    'HEED': HeedBaseline,
    'PEGASIS': PegasisBaseline,
    'DeepSensor': DrlBaseline,
    'FL-Energy': FlEnergyBaseline,
}

scales = [100, 200, 300, 500]

for name, cls in protocols.items():
    print(f"\n{'='*60}")
    print(f" {name}")
    print(f"{'='*60}")
    print(f"{'Scale':<8} {'HND':>8} {'Jain':>8} {'Delivery':>10} {'Alive':>8} {'EnergyEff':>10}")
    print("-" * 60)
    for scale in scales:
        config = SimConfig(num_nodes=scale, max_iterations=300, num_runs=30, random_seed=42)
        proto = cls(config)
        proto.initialize()
        for r in range(300):
            proto.step(r)
        result = proto.get_result()
        alive = sum(1 for n in proto.nodes if n.energy_residual > 0.01 * n.energy_initial)
        flag = " !" if (result.hnd_mean == 300.0 and result.jains_fairness < 0.001) else ""
        print(f"{scale:<8} {result.hnd_mean:>8.1f} {result.jains_fairness:>8.4f} "
              f"{result.delivery_ratio_mean:>10.4f} {alive:>5}/{scale:<5} "
              f"{result.energy_efficiency:>10.4f}{flag}")

# Ours
print(f"\n{'='*60}")
print(" Ours")
print(f"{'='*60}")
print(f"{'Scale':<8} {'HND':>8} {'Jain':>8} {'Delivery':>10} {'Alive':>8} {'EnergyEff':>10} {'Converged':>10}")
print("-" * 70)
for scale in scales:
    config = SimConfig(num_nodes=scale, max_iterations=300, num_runs=30, random_seed=42)
    orch = TwoLayerOrchestrator(config)
    result = orch.run()
    alive = sum(1 for n in orch.nodes if n.energy_residual > 0.01 * n.energy_initial)
    conv = getattr(orch, 'converged_at', 300)
    print(f"{scale:<8} {result.hnd_mean:>8.1f} {result.jains_fairness:>8.4f} "
          f"{result.delivery_ratio_mean:>10.4f} {alive:>5}/{scale:<5} "
          f"{result.energy_efficiency:>10.4f} {conv:>10}")

print("\nAll cross-scale checks complete.")