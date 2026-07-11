"""Comprehensive smoke test: all protocols at scale 500."""
import sys
sys.path.insert(0, '.')
from run_experiment import (
    LeachBaseline, HeedBaseline, PegasisBaseline,
    DrlBaseline, FlEnergyBaseline, TwoLayerOrchestrator, SimConfig
)

config = SimConfig(num_nodes=500, max_iterations=300, num_runs=30, random_seed=42)

protocols = {
    'LEACH': lambda: LeachBaseline(SimConfig(num_nodes=500, max_iterations=300, num_runs=30, random_seed=42)),
    'HEED': lambda: HeedBaseline(SimConfig(num_nodes=500, max_iterations=300, num_runs=30, random_seed=42)),
    'PEGASIS': lambda: PegasisBaseline(SimConfig(num_nodes=500, max_iterations=300, num_runs=30, random_seed=42)),
    'DeepSensor': lambda: DrlBaseline(SimConfig(num_nodes=500, max_iterations=300, num_runs=30, random_seed=42)),
    'FL-Energy': lambda: FlEnergyBaseline(SimConfig(num_nodes=500, max_iterations=300, num_runs=30, random_seed=42)),
}

print(f"{'Protocol':<14} {'HND':>8} {'Jain':>8} {'Delivery':>10} {'Alive':>8} {'EnergyEff':>10} {'Status'}")
print("-" * 75)

anomalies = []

for name, factory in protocols.items():
    proto = factory()
    proto.initialize()
    for r in range(300):
        proto.step(r)
    result = proto.get_result()
    alive = sum(1 for n in proto.nodes if n.energy_residual > 0.01 * n.energy_initial)
    status = "OK"
    if result.hnd_mean == 300.0 and result.jains_fairness == 0.0:
        status = "ANOMALY"
        anomalies.append(name)
    elif result.hnd_mean == 300.0:
        status = "BORDERLINE"
        anomalies.append(name)
    elif result.jains_fairness < 0.01:
        status = "LOW_JAIN"
    print(f"{name:<14} {result.hnd_mean:>8.1f} {result.jains_fairness:>8.4f} {result.delivery_ratio_mean:>10.4f} {alive:>5}/500 {result.energy_efficiency:>10.4f} {status}")

# Test Ours
config2 = SimConfig(num_nodes=500, max_iterations=300, num_runs=30, random_seed=42)
orch = TwoLayerOrchestrator(config2)
result = orch.run()
alive = sum(1 for n in orch.nodes if n.energy_residual > 0.01 * n.energy_initial)
status = "OK"
if result.hnd_mean == 300.0 and result.jains_fairness == 0.0:
    status = "ANOMALY"
    anomalies.append('Ours')
print(f"{'Ours':<14} {result.hnd_mean:>8.1f} {result.jains_fairness:>8.4f} {result.delivery_ratio_mean:>10.4f} {alive:>5}/500 {result.energy_efficiency:>10.4f} {status}")

print()
if anomalies:
    print(f"ANOMALIES DETECTED: {anomalies}")
else:
    print("All protocols: no data anomalies detected.")