"""DeepSensor and FL-Energy deep analysis at scale 500."""
import sys
sys.path.insert(0, '.')
from run_experiment import DrlBaseline, FlEnergyBaseline, SimConfig

# DeepSensor deep dive
config = SimConfig(num_nodes=500, max_iterations=300, num_runs=30, random_seed=42)
ds = DrlBaseline(config)
ds.initialize()
for r in range(300):
    ds.step(r)

alive = [n for n in ds.nodes if n.energy_residual > 0.01 * n.energy_initial]
dead = [n for n in ds.nodes if n.energy_residual <= 0.01 * n.energy_initial]
print("=== DeepSensor @ 500 ===")
print(f"Alive: {len(alive)}, Dead: {len(dead)}")
if alive:
    avg_tau_alive = sum(n.x.tau for n in alive) / len(alive)
    avg_energy_alive = sum(n.energy_residual/n.energy_initial for n in alive) / len(alive)
    print(f"Alive avg tau: {avg_tau_alive:.4f}, avg residual ratio: {avg_energy_alive:.4f}")
if dead:
    avg_tau_dead = sum(n.x.tau for n in dead) / len(dead)
    avg_residual_dead = sum(n.energy_residual/n.energy_initial for n in dead) / len(dead)
    print(f"Dead avg tau: {avg_tau_dead:.4f}, avg residual ratio: {avg_residual_dead:.6f}")

# Policy distribution
taus = [n.x.tau for n in ds.nodes]
taus_sorted = sorted(taus)
print(f"Tau distribution: min={min(taus):.3f}, p25={taus_sorted[125]:.3f}, "
      f"median={taus_sorted[250]:.3f}, p75={taus_sorted[375]:.3f}, max={max(taus):.3f}")

# Check: is HND computed from alive nodes or fallback?
result = ds.get_result()
print(f"HND: {result.hnd_mean:.1f}, Jain: {result.jains_fairness:.4f}")
print(f"HND == max_iterations? {result.hnd_mean == 300.0}")

# Verify HND computation manually
total_consumed = 0.0
alive_count = 0
for node in ds.nodes:
    consumed = node.energy_initial - node.energy_residual
    if consumed > 0 and node.energy_residual > 0.01 * node.energy_initial:
        total_consumed += consumed
        alive_count += 1
print(f"Manual check: alive_count={alive_count}, total_consumed={total_consumed:.1f}")
if alive_count > 0:
    avg_cons = total_consumed / alive_count / 300
    avg_init = sum(n.energy_initial for n in ds.nodes) / 500
    print(f"Manual HND: {avg_init/avg_cons:.1f}")

# Also check if all-dead fallback would trigger
if alive_count == 0:
    total_all = sum(max(0.0, n.energy_initial - n.energy_residual) for n in ds.nodes)
    print(f"All-dead fallback: total_all={total_all:.1f}, would be HND={2250/(total_all/500/300):.1f}")

print()

# FL-Energy deep dive
fl = FlEnergyBaseline(config)
fl.initialize()
for r in range(300):
    fl.step(r)

alive_fl = [n for n in fl.nodes if n.energy_residual > 0.01 * n.energy_initial]
dead_fl = [n for n in fl.nodes if n.energy_residual <= 0.01 * n.energy_initial]
print("=== FL-Energy @ 500 ===")
print(f"Alive: {len(alive_fl)}, Dead: {len(dead_fl)}")
if alive_fl:
    avg_initial_alive = sum(n.energy_initial for n in alive_fl) / len(alive_fl)
    avg_consumed_alive = sum(n.energy_initial - n.energy_residual for n in alive_fl) / len(alive_fl)
    print(f"Alive avg initial energy: {avg_initial_alive:.1f} mJ")
    print(f"Alive avg consumed: {avg_consumed_alive:.1f} mJ")
    print(f"Alive per-round consumption: {avg_consumed_alive/300:.3f} mJ")
if dead_fl:
    avg_initial_dead = sum(n.energy_initial for n in dead_fl) / len(dead_fl)
    avg_consumed_dead = sum(n.energy_initial - n.energy_residual for n in dead_fl) / len(dead_fl)
    print(f"Dead avg initial energy: {avg_initial_dead:.1f} mJ")
    print(f"Dead avg consumed: {avg_consumed_dead:.1f} mJ")

# Check tau uniformity
taus_fl = set(round(n.x.tau, 6) for n in fl.nodes)
print(f"Unique tau values: {len(taus_fl)} (should be 1)")
print(f"Tau value: {list(taus_fl)[0] if len(taus_fl) == 1 else 'multiple'}")

result_fl = fl.get_result()
print(f"HND: {result_fl.hnd_mean:.1f}, Jain: {result_fl.jains_fairness:.4f}")

# Theoretical HND
comm_overhead = 1.2 * (1.0 + 0.001 * 500)
tx = 0.5 * 17.4 * 3.0 * 0.1 * comm_overhead
rx = 0.5 * 19.7 * 3.0 * 0.1 * 0.6 * (1.0 + 0.001 * 500)
idle = 0.5 * 0.2 * 1.0 * 3.0 * 0.1
total_per_round = tx + rx + idle
print(f"Theoretical per-round: tx={tx:.3f}, rx={rx:.3f}, idle={idle:.3f}, total={total_per_round:.3f}")
print(f"Theoretical HND: {2250/total_per_round:.1f}")
print(f"Nodes that should survive (> {total_per_round*300:.1f} mJ initial): "
      f"{(2500-total_per_round*300)/500*500:.0f}/500")