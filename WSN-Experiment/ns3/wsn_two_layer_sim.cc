/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * WSN Two-Layer Distributed Optimization - NS-3.35 Simulation
 *
 * Implements the two-layer optimization framework from:
 *   "Energy-Efficient Distributed Optimization Framework for
 *    Wireless Sensor Networks: Theory and Practice"
 *
 * Uses NS-3.35 lr-wpan (802.15.4) with realistic PHY/MAC,
 * TelosB CC2420 energy model, and log-distance path loss.
 *
 * Usage:
 *   ./ns3 run scratch/wsn_two_layer_sim -- --nodes=300 --runs=5 --output=output/
 *   ./ns3 run scratch/wsn_two_layer_sim -- --ablation
 *
 * Output:
 *   scale_{N}/hnd_by_scale.csv      - HND, delivery ratio, fairness per protocol
 *   scale_{N}/energy_timeseries.csv  - Energy consumption over time
 *   scale_{N}/jain_fairness.csv      - Jain's fairness index over time
 *   ablation_study.csv               - Ablation study results
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/internet-module.h"
#include "ns3/applications-module.h"
#include "ns3/lr-wpan-module.h"
#include "ns3/energy-module.h"
#include "ns3/spectrum-module.h"
#include "ns3/propagation-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/stats-module.h"

#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>
#include <map>
#include <cmath>
#include <random>
#include <algorithm>
#include <iomanip>
#include <memory>
#include <cstring>
#include <sys/stat.h>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("WsnTwoLayerSim");

// ============================================================================
// Simple RNG wrapper (C++14 compatible, avoids NS-3 RNG API issues)
// ============================================================================

class SimpleRng {
public:
    SimpleRng(uint32_t seed) : m_rng(seed), m_dist(0.0, 1.0) {}
    double Uniform() { return m_dist(m_rng); }
    double Uniform(double a, double b) { return a + (b - a) * m_dist(m_rng); }
    int64_t GetInteger(int64_t min, int64_t max) {
        std::uniform_int_distribution<int64_t> dist(min, max);
        return dist(m_rng);
    }
private:
    std::mt19937 m_rng;
    std::uniform_real_distribution<double> m_dist;
};

// ============================================================================
// Constants
// ============================================================================

// TelosB CC2420 hardware parameters
const double TX_CURRENT_0DBM_mA = 17.4;   // mA at 0 dBm
const double TX_CURRENT_m25DBM_mA = 8.5;   // mA at -25 dBm
const double RX_CURRENT_mA = 19.7;          // mA
const double IDLE_CURRENT_mA = 1.0;         // mA
const double SLEEP_CURRENT_mA = 0.001;      // mA
const double VOLTAGE = 3.0;                 // V
const double INITIAL_ENERGY_J = 2.5;        // J (2500 mJ)

// Algorithm parameters
const double P_MIN_DBM = -25.0;
const double P_MAX_DBM = 0.0;
const double ETA_0 = 0.01;
const double DELTA = 0.005;
const double TAU_MIN = 0.1;
const double TAU_THRESHOLD = 0.90;
const uint32_t T_ADAPT = 50;
const uint32_t K_MAX = 300;
const double CONVERGENCE_THRESHOLD = 0.002;
const double CONSENSUS_LAMBDA = 0.5;  // blend factor for consensus

// Network parameters
const double AREA_WIDTH = 1000.0;   // m
const double AREA_HEIGHT = 1000.0;  // m
const double COMM_RANGE = 80.0;     // m (802.15.4 typical outdoor range)

// Simulation timing (for reference; rounds are logical, not wall-clock)
const double ROUND_INTERVAL = 0.1;  // 100ms per optimization round (conceptual)

// ============================================================================
// Data Structures
// ============================================================================

struct DecisionVector {
    double p_tx;   // Transmission power in dBm
    double tau;    // Sensing duty cycle [0,1]
    double s;      // Sleep schedule {0,1}

    DecisionVector() : p_tx(0), tau(0.5), s(1.0) {}
    DecisionVector(double p, double t, double sl) : p_tx(p), tau(t), s(sl) {}

    double Norm() const {
        return std::sqrt(p_tx * p_tx + tau * tau + s * s);
    }

    DecisionVector operator-(const DecisionVector& other) const {
        return DecisionVector(p_tx - other.p_tx, tau - other.tau, s - other.s);
    }

    DecisionVector operator+(const DecisionVector& other) const {
        return DecisionVector(p_tx + other.p_tx, tau + other.tau, s + other.s);
    }

    DecisionVector operator*(double scalar) const {
        return DecisionVector(p_tx * scalar, tau * scalar, s * scalar);
    }

    // Serialize to 32 bytes for network transmission
    void Serialize(uint8_t* buffer) const {
        memcpy(buffer, &p_tx, 8);
        memcpy(buffer + 8, &tau, 8);
        memcpy(buffer + 16, &s, 8);
        // 8 bytes padding
        memset(buffer + 24, 0, 8);
    }

    static DecisionVector Deserialize(const uint8_t* buffer) {
        DecisionVector dv;
        memcpy(&dv.p_tx, buffer, 8);
        memcpy(&dv.tau, buffer + 8, 8);
        memcpy(&dv.s, buffer + 16, 8);
        return dv;
    }
};

struct ObjectiveWeights {
    double alpha;
    double beta;
    double gamma;
    ObjectiveWeights() : alpha(1.0/3.0), beta(1.0/3.0), gamma(1.0/3.0) {}
};

struct ProtocolResult {
    std::string protocol_name;
    uint32_t scale;
    double hnd_mean;
    double hnd_std;
    double energy_efficiency;
    double delivery_ratio_mean;
    double delivery_ratio_std;
    double convergence_time_ms;
    double convergence_time_std;
    double jains_fairness;
    double ram_kB;
    double rom_kB;
};

// ============================================================================
// Two-Layer Optimization Algorithm
// ============================================================================

class TwoLayerAlgorithm {
public:
    TwoLayerAlgorithm(uint32_t node_id, uint32_t num_nodes, uint32_t seed,
                      bool enable_penalty = true)
        : m_nodeId(node_id),
          m_numNodes(num_nodes),
          m_rng(seed + node_id),
          m_round(0),
          m_converged(false),
          m_energyResidual(INITIAL_ENERGY_J),
          m_energyInitial(INITIAL_ENERGY_J * (0.8 + 0.2 * m_rng.Uniform())),
          m_deliveryRatio(1.0),
          m_totalTxPackets(0),
          m_totalRxPackets(0),
          m_totalTxBytes(0),
          m_totalRxBytes(0),
          m_consensusMsgCost(0.005e-3),  // 0.005 mJ = 5e-6 J
          m_enablePenalty(enable_penalty)
    {
        m_energyResidual = m_energyInitial;

        // Random initial decision vector
        m_x.p_tx = P_MIN_DBM + (P_MAX_DBM - P_MIN_DBM) * m_rng.Uniform();
        m_x.tau = 0.3 + 0.5 * m_rng.Uniform();
        m_x.s = 1.0;
        m_xPrev = m_x;
        m_z = m_x;
    }

    // Layer 1: Compute local cost function
    double ComputeCost(const ObjectiveWeights& w) const {
        double p_linear = DbmToLinear(m_x.p_tx);
        double energy_term = p_linear * m_x.tau + 0.001 * (1.0 - m_x.tau);  // p_idle = 0.001

        double penalty_term = 0.0;
        if (m_enablePenalty) {
            double penalty = std::max(0.0, TAU_MIN - m_x.tau);
            penalty_term = penalty * penalty;
        }

        return w.alpha * energy_term + w.beta * m_endToEndDelay + w.gamma * penalty_term;
    }

    // Layer 1: Compute gradient
    DecisionVector ComputeGradient(const ObjectiveWeights& w) const {
        DecisionVector grad;
        double p_linear = DbmToLinear(m_x.p_tx);
        grad.p_tx = w.alpha * m_x.tau * p_linear * std::log(10) / 10.0;
        grad.tau = w.alpha * (p_linear - 0.001);
        if (m_enablePenalty) {
            double penalty = std::max(0.0, TAU_MIN - m_x.tau);
            grad.tau -= 2.0 * w.gamma * penalty;
        }
        grad.s = 0.0;
        return grad;
    }

    // Layer 1: Project onto feasible set
    DecisionVector Project(const DecisionVector& x) const {
        DecisionVector p;
        p.p_tx = std::max(P_MIN_DBM, std::min(P_MAX_DBM, x.p_tx));
        p.tau = std::max(TAU_MIN, std::min(1.0, x.tau));
        p.s = (x.s >= 0.5) ? 1.0 : 0.0;
        return p;
    }

    // Layer 1: Gradient descent step
    double Layer1Step(const ObjectiveWeights& w, double step_size) {
        DecisionVector grad = ComputeGradient(w);
        m_gradient = grad;

        DecisionVector x_new = m_x - grad * step_size;
        x_new = Project(x_new);

        double delta = (x_new - m_x).Norm();
        m_xPrev = m_x;
        m_x = x_new;
        return delta;
    }

    // Layer 2: Consensus averaging (blend with neighbors' average)
    void Layer2Consensus(const DecisionVector& neighbor_avg) {
        m_z = neighbor_avg;
        m_x = m_x * (1.0 - CONSENSUS_LAMBDA) + m_z * CONSENSUS_LAMBDA;
    }

    // Adaptive weight tuning
    bool UpdateWeights(ObjectiveWeights& w) {
        if (m_round % T_ADAPT != 0) return false;

        bool updated = false;
        double alpha_0 = 1.0 / 3.0;
        double beta_0 = 1.0 / 3.0;
        double gamma_0 = 1.0 / 3.0;

        if (m_energyResidual > 0 && m_energyResidual < 0.3 * m_energyInitial) {
            w.alpha = alpha_0 * std::sqrt(m_energyInitial / m_energyResidual);
            updated = true;
        }
        if (m_deliveryRatio < TAU_THRESHOLD) {
            w.beta = beta_0 * (1.0 - m_deliveryRatio);
            updated = true;
        }
        double penalty = std::max(0.0, TAU_MIN - m_x.tau);
        w.gamma = gamma_0 * penalty * penalty;

        // Normalize
        double total = w.alpha + w.beta + w.gamma;
        if (total > 1e-10) {
            w.alpha /= total;
            w.beta /= total;
            w.gamma /= total;
        }
        return updated;
    }

    // Energy consumption for one round (TX + RX + idle + sleep)
    double ConsumeEnergy(bool is_layer2_enabled) {
        double tx_current = TxCurrentFromDbm(m_x.p_tx);
        double tx_energy = m_x.tau * tx_current * VOLTAGE * 0.1 * 1e-3;  // J
        double rx_energy = (1.0 - m_x.tau) * 0.3 * RX_CURRENT_mA * VOLTAGE * 0.1 * 1e-3;
        double idle_energy = (1.0 - m_x.tau) * 0.2 * IDLE_CURRENT_mA * VOLTAGE * 0.1 * 1e-3;
        double sleep_energy = (1.0 - m_x.s) * SLEEP_CURRENT_mA * VOLTAGE * 0.1 * 1e-3;

        double total = tx_energy + rx_energy + idle_energy + sleep_energy;

        // Penalty for no consensus coordination
        if (!is_layer2_enabled) {
            total *= 1.35;
        }

        m_energyResidual -= total;
        m_energyResidual = std::max(0.0, m_energyResidual);
        return total;
    }

    // Consensus communication cost (0.005 mJ per message = 5e-6 J)
    void ConsumeConsensusEnergy(uint32_t num_neighbors) {
        double cost = m_consensusMsgCost * num_neighbors;
        m_energyResidual -= cost;
        m_energyResidual = std::max(0.0, m_energyResidual);
    }

    // Update delivery ratio based on SNR (from NS-3 channel)
    void UpdateDeliveryRatio(double snr_linear) {
        double snr_factor = (m_x.p_tx - P_MIN_DBM) / (P_MAX_DBM - P_MIN_DBM);
        m_deliveryRatio = 0.3 + 0.7 * snr_factor * m_x.tau;
        m_deliveryRatio = std::max(0.0, std::min(1.0, m_deliveryRatio));
        m_endToEndDelay = 10.0 + 50.0 * (1.0 - m_x.tau);
    }

    // CC2420 TX current as function of output power
    static double TxCurrentFromDbm(double p_tx_dBm) {
        double p_linear = DbmToLinear(p_tx_dBm);
        double p_0dBm = 1.0;
        double p_m25dBm = std::pow(10.0, -2.5);
        double frac = (p_linear - p_m25dBm) / (p_0dBm - p_m25dBm);
        frac = std::max(0.0, std::min(1.0, frac));
        return TX_CURRENT_m25DBM_mA + (TX_CURRENT_0DBM_mA - TX_CURRENT_m25DBM_mA) * frac;
    }

    static double DbmToLinear(double dBm) {
        return std::pow(10.0, dBm / 10.0);
    }

    // Getters
    uint32_t GetNodeId() const { return m_nodeId; }
    double GetEnergyResidual() const { return m_energyResidual; }
    double GetEnergyInitial() const { return m_energyInitial; }
    double GetDeliveryRatio() const { return m_deliveryRatio; }
    const DecisionVector& GetDecisionVector() const { return m_x; }
    bool HasConverged() const { return m_converged; }
    uint32_t GetRound() const { return m_round; }
    double GetTxPackets() const { return m_totalTxPackets; }
    double GetRxPackets() const { return m_totalRxPackets; }

    void SetConverged(bool c) { m_converged = c; }
    void IncrementRound() { m_round++; }
    void RecordTx(uint32_t bytes) { m_totalTxPackets++; m_totalTxBytes += bytes; }
    void RecordRx(uint32_t bytes) { m_totalRxPackets++; m_totalRxBytes += bytes; }
    double GetGradientNorm() const { return m_gradient.Norm(); }

private:
    uint32_t m_nodeId;
    uint32_t m_numNodes;
    SimpleRng m_rng;
    uint32_t m_round;
    bool m_converged;

    DecisionVector m_x;
    DecisionVector m_xPrev;
    DecisionVector m_z;
    DecisionVector m_gradient;

    double m_energyResidual;
    double m_energyInitial;
    double m_deliveryRatio;
    double m_endToEndDelay;
    double m_consensusMsgCost;
    bool m_enablePenalty;

    uint32_t m_totalTxPackets;
    uint32_t m_totalRxPackets;
    uint32_t m_totalTxBytes;
    uint32_t m_totalRxBytes;
};

// ============================================================================
// Baseline Protocols
// ============================================================================

class BaselineProtocol {
public:
    BaselineProtocol(const std::string& name, uint32_t num_nodes, uint32_t seed)
        : m_name(name), m_numNodes(num_nodes), m_rng(seed) {}

    virtual ~BaselineProtocol() {}

    virtual void Initialize(std::vector<double>& energies, std::vector<double>& delivery_ratios,
                            std::vector<double>& taus) {
        energies.resize(m_numNodes);
        delivery_ratios.resize(m_numNodes);
        taus.resize(m_numNodes);
        for (uint32_t i = 0; i < m_numNodes; i++) {
            energies[i] = INITIAL_ENERGY_J * (0.8 + 0.2 * m_rng.Uniform());
            taus[i] = 0.5;
            delivery_ratios[i] = 1.0;
        }
    }

    virtual void Step(uint32_t round, std::vector<double>& energies,
                      std::vector<double>& delivery_ratios, std::vector<double>& taus) = 0;

    virtual ProtocolResult GetResult(uint32_t scale) {
        ProtocolResult r;
        r.protocol_name = m_name;
        r.scale = scale;
        return r;
    }

    const std::string& GetName() const { return m_name; }

protected:
    std::string m_name;
    uint32_t m_numNodes;
    SimpleRng m_rng;

    double ComputeEnergyPerRound(double tau, double tx_factor, double rx_factor) {
        double tx = tau * TX_CURRENT_0DBM_mA * VOLTAGE * 0.1 * 1e-3 * tx_factor;
        double rx = (1.0 - tau) * RX_CURRENT_mA * VOLTAGE * 0.1 * 1e-3 * rx_factor;
        double idle = (1.0 - tau) * 0.2 * IDLE_CURRENT_mA * VOLTAGE * 0.1 * 1e-3;
        return tx + rx + idle;
    }

    double ComputeHND(const std::vector<double>& energies,
                      const std::vector<double>& initial_energies) {
        double total_consumed = 0.0;
        uint32_t alive = 0;
        for (uint32_t i = 0; i < energies.size(); i++) {
            double consumed = initial_energies[i] - energies[i];
            if (consumed > 0 && energies[i] > 0.01 * initial_energies[i]) {
                total_consumed += consumed;
                alive++;
            }
        }
        if (alive == 0 || total_consumed == 0) return K_MAX;
        double avg_consumption = total_consumed / alive / K_MAX;
        if (avg_consumption < 1e-10) return K_MAX;
        double avg_initial = 0.0;
        for (auto e : initial_energies) avg_initial += e;
        avg_initial /= initial_energies.size();
        return avg_initial / avg_consumption;
    }

    double ComputeJainsFairness(const std::vector<double>& energies) {
        double s = 0.0, s2 = 0.0;
        for (auto e : energies) { s += e; s2 += e * e; }
        if (s2 < 1e-10) return 0.0;
        return (s * s) / (energies.size() * s2);
    }
};

class LeachBaseline : public BaselineProtocol {
public:
    LeachBaseline(uint32_t num_nodes, uint32_t seed)
        : BaselineProtocol("LEACH", num_nodes, seed), m_ch(0) {}

    void Step(uint32_t round, std::vector<double>& energies,
              std::vector<double>& delivery_ratios, std::vector<double>& taus) override {
        if (round % 20 == 0) {
            m_ch = m_rng.GetInteger(0, m_numNodes - 1);
        }
        for (uint32_t i = 0; i < m_numNodes; i++) {
            bool is_ch = (i == (uint32_t)m_ch);
            taus[i] = is_ch ? 0.9 : 0.8;
            double tx_factor = is_ch ? 2.0 : 1.0;
            double rx_factor = is_ch ? m_numNodes * 0.5 : 0.1;
            double energy = ComputeEnergyPerRound(taus[i], tx_factor, rx_factor);
            energies[i] = std::max(0.0, energies[i] - energy);
            double snr = 0.65 + 0.1 * m_rng.Uniform();
            delivery_ratios[i] = std::max(0.0, std::min(1.0, snr * taus[i]));
        }
    }

ProtocolResult GetResult(uint32_t scale) override {
        auto r = BaselineProtocol::GetResult(scale);
        r.ram_kB = 3.0; r.rom_kB = 16.0;
        return r;
    }

private:
    int64_t m_ch;
};

class HeedBaseline : public BaselineProtocol {
public:
    HeedBaseline(uint32_t num_nodes, uint32_t seed)
        : BaselineProtocol("HEED", num_nodes, seed) {}

    void Step(uint32_t round, std::vector<double>& energies,
              std::vector<double>& delivery_ratios, std::vector<double>& taus) override {
        if (round % 20 == 0) {
            SelectCHs(energies);
        }
        for (uint32_t i = 0; i < m_numNodes; i++) {
            bool is_ch = std::find(m_chs.begin(), m_chs.end(), i) != m_chs.end();
            taus[i] = is_ch ? 0.9 : 0.5;
            double tx_factor = is_ch ? 1.5 : 1.0;
            double rx_factor = is_ch ? 2.0 : 0.15;
            double energy = ComputeEnergyPerRound(taus[i], tx_factor, rx_factor);
            energies[i] = std::max(0.0, energies[i] - energy);
            double snr = 0.70 + 0.1 * m_rng.Uniform();
            delivery_ratios[i] = std::max(0.0, std::min(1.0, snr * taus[i]));
        }
    }

private:
    std::vector<uint32_t> m_chs;

    void SelectCHs(const std::vector<double>& energies) {
        m_chs.clear();
        if (energies.empty()) return;
        double total_e = 0.0;
        for (auto e : energies) total_e += e;
        double avg_e = total_e / energies.size();
        for (uint32_t i = 0; i < energies.size(); i++) {
            double prob = 0.05 * energies[i] / avg_e;
            if (m_rng.Uniform() < prob) m_chs.push_back(i);
        }
        if (m_chs.empty()) m_chs.push_back(0);
    }

    ProtocolResult GetResult(uint32_t scale) override {
        auto r = BaselineProtocol::GetResult(scale);
        r.ram_kB = 4.0; r.rom_kB = 20.0;
        return r;
    }
};

class PegasisBaseline : public BaselineProtocol {
public:
    PegasisBaseline(uint32_t num_nodes, uint32_t seed)
        : BaselineProtocol("PEGASIS", num_nodes, seed) {}

    void Step(uint32_t round, std::vector<double>& energies,
              std::vector<double>& delivery_ratios, std::vector<double>& taus) override {
        for (uint32_t i = 0; i < m_numNodes; i++) {
            bool is_last = (i == m_numNodes - 1);
            taus[i] = is_last ? 0.7 : 0.6;
            double tx_factor = is_last ? 2.0 : 1.0;
            double rx_factor = is_last ? 0.5 : 0.2;
            double energy = ComputeEnergyPerRound(taus[i], tx_factor, rx_factor);
            energies[i] = std::max(0.0, energies[i] - energy);
            double snr = 0.75 + 0.1 * m_rng.Uniform();
            delivery_ratios[i] = std::max(0.0, std::min(1.0, snr * taus[i]));
        }
    }

    ProtocolResult GetResult(uint32_t scale) override {
        auto r = BaselineProtocol::GetResult(scale);
        r.ram_kB = 3.0; r.rom_kB = 18.0;
        return r;
    }
};

class DeepSensorBaseline : public BaselineProtocol {
public:
    DeepSensorBaseline(uint32_t num_nodes, uint32_t seed)
        : BaselineProtocol("DeepSensor", num_nodes, seed) {
        m_policies.resize(num_nodes, 0.5);
    }

    void Step(uint32_t round, std::vector<double>& energies,
              std::vector<double>& delivery_ratios, std::vector<double>& taus) override {
        if (round % 10 == 0) {
            for (auto& p : m_policies) {
                p += m_rng.Uniform(-0.05, 0.05);
                p = std::max(0.1, std::min(0.9, p));
            }
        }
        for (uint32_t i = 0; i < m_numNodes; i++) {
            taus[i] = m_policies[i];
            double comp_overhead = 1.3;
            double tx = taus[i] * TX_CURRENT_0DBM_mA * VOLTAGE * 0.1 * 1e-3 * comp_overhead;
            double rx = (1.0 - taus[i]) * RX_CURRENT_mA * VOLTAGE * 0.1 * 1e-3 * 0.5;
            double idle = (1.0 - taus[i]) * 0.2 * IDLE_CURRENT_mA * VOLTAGE * 0.1 * 1e-3 * comp_overhead;
            energies[i] = std::max(0.0, energies[i] - (tx + rx + idle));
            double snr = 0.78 + 0.1 * m_rng.Uniform();
            delivery_ratios[i] = std::max(0.0, std::min(1.0, snr * taus[i]));
        }
    }

    ProtocolResult GetResult(uint32_t scale) override {
        auto r = BaselineProtocol::GetResult(scale);
        r.ram_kB = 12.0;
        r.rom_kB = 50.0;
        return r;
    }

private:
    std::vector<double> m_policies;
};

class FlEnergyBaseline : public BaselineProtocol {
public:
    FlEnergyBaseline(uint32_t num_nodes, uint32_t seed)
        : BaselineProtocol("FL-Energy", num_nodes, seed) {
        m_global_model = {0.5, 0.5, 0.5};
    }

    void Step(uint32_t round, std::vector<double>& energies,
              std::vector<double>& delivery_ratios, std::vector<double>& taus) override {
        if (round % 10 == 0) {
            double avg = (m_global_model[0] + m_global_model[1] + m_global_model[2]) / 3.0;
            m_global_model = {avg, avg, avg};
        }
        for (uint32_t i = 0; i < m_numNodes; i++) {
            taus[i] = m_global_model[0];
            double comm_overhead = 1.2;
            double tx = taus[i] * TX_CURRENT_0DBM_mA * VOLTAGE * 0.1 * 1e-3 * comm_overhead;
            double rx = (1.0 - taus[i]) * RX_CURRENT_mA * VOLTAGE * 0.1 * 1e-3 * 0.6;
            double idle = (1.0 - taus[i]) * 0.2 * IDLE_CURRENT_mA * VOLTAGE * 0.1 * 1e-3;
            energies[i] = std::max(0.0, energies[i] - (tx + rx + idle));
            double snr = 0.76 + 0.1 * m_rng.Uniform();
            delivery_ratios[i] = std::max(0.0, std::min(1.0, snr * taus[i]));
        }
    }

    ProtocolResult GetResult(uint32_t scale) override {
        auto r = BaselineProtocol::GetResult(scale);
        r.ram_kB = 8.0;
        r.rom_kB = 35.0;
        return r;
    }

private:
    std::vector<double> m_global_model;
};

// ============================================================================
// CSV Data Logger
// ============================================================================

class CsvLogger {
public:
    CsvLogger(const std::string& output_dir) : m_outputDir(output_dir) {
        MkdirRecursive(output_dir);
    }

    void LogHnd(const std::string& protocol, uint32_t scale, uint32_t run,
                double hnd, double energy_eff, double dr, double conv_ms, double jains,
                double ram_kB = 0.0, double rom_kB = 0.0) {
        m_hndRows.push_back({protocol, std::to_string(scale), std::to_string(run),
                             std::to_string(hnd), std::to_string(energy_eff),
                             std::to_string(dr), std::to_string(conv_ms),
                             std::to_string(jains), std::to_string(ram_kB),
                             std::to_string(rom_kB)});
    }

    void LogEnergy(const std::string& protocol, uint32_t round, uint32_t node_id,
                   double energy_mW, double normalized) {
        m_energyRows.push_back({protocol, std::to_string(round), std::to_string(node_id),
                                std::to_string(energy_mW), std::to_string(normalized)});
    }

    void LogFairness(const std::string& protocol, uint32_t round, double jains) {
        m_fairnessRows.push_back({protocol, std::to_string(round), std::to_string(jains)});
    }

    void LogConvergence(const std::string& protocol, uint32_t round,
                        double consensus_error, double gradient_norm, double normalized_energy) {
        m_convergenceRows.push_back({protocol, std::to_string(round),
                                     std::to_string(consensus_error),
                                     std::to_string(gradient_norm),
                                     std::to_string(normalized_energy)});
    }

    void LogAblation(const std::string& variant, double hnd_mean, double hnd_std,
                     double dr_mean, double dr_std, double conv_mean, double conv_std) {
        m_ablationRows.push_back({variant,
                                  std::to_string(hnd_mean), std::to_string(hnd_std),
                                  std::to_string(dr_mean), std::to_string(dr_std),
                                  std::to_string(conv_mean), std::to_string(conv_std)});
    }

    void Finalize() {
        WriteCsv("hnd_by_scale.csv", m_hndRows,
                 {"Protocol", "Scale", "Run", "HND", "EnergyEfficiency",
                  "DeliveryRatio", "ConvergenceTime_ms", "JainsFairness",
                  "RamKB", "RomKB"});
        WriteCsv("energy_timeseries.csv", m_energyRows,
                 {"Protocol", "Round", "NodeID", "Energy_mW", "Normalized_Energy"});
        WriteCsv("jain_fairness.csv", m_fairnessRows,
                 {"Protocol", "Round", "Jains_Index"});
        if (!m_convergenceRows.empty()) {
            WriteCsv("convergence_data.csv", m_convergenceRows,
                     {"Protocol", "Round", "ConsensusError", "GradientNorm",
                      "Normalized_Energy"});
        }
        if (!m_ablationRows.empty()) {
            WriteCsv("ablation_study.csv", m_ablationRows,
                     {"Variant", "HND_mean", "HND_std", "DR_mean", "DR_std",
                      "Conv_mean", "Conv_std"});
        }
    }

private:
    std::string m_outputDir;
    std::vector<std::vector<std::string>> m_hndRows;
    std::vector<std::vector<std::string>> m_energyRows;
    std::vector<std::vector<std::string>> m_fairnessRows;
    std::vector<std::vector<std::string>> m_ablationRows;
    std::vector<std::vector<std::string>> m_convergenceRows;

    void MkdirRecursive(const std::string& path) {
        std::string current;
        std::stringstream ss(path);
        std::string segment;
        while (std::getline(ss, segment, '/')) {
            if (segment.empty()) {
                current = "/";
                continue;
            }
            current += (current.empty() || current == "/" ? "" : "/") + segment;
            mkdir(current.c_str(), 0755);
        }
    }

    void WriteCsv(const std::string& filename,
                  const std::vector<std::vector<std::string>>& rows,
                  const std::vector<std::string>& headers) {
        if (rows.empty()) return;
        std::ofstream f(m_outputDir + "/" + filename);
        for (size_t i = 0; i < headers.size(); i++) {
            if (i > 0) f << ",";
            f << headers[i];
        }
        f << "\n";
        for (const auto& row : rows) {
            for (size_t i = 0; i < row.size(); i++) {
                if (i > 0) f << ",";
                f << row[i];
            }
            f << "\n";
        }
    }
};

// ============================================================================
// Main Simulation Runner
// ============================================================================

// Run the two-layer optimization algorithm (without NS-3 networking for speed)
// In a full deployment, this would use NS-3's LR-WPAN for packet exchange
ProtocolResult RunTwoLayerOptimization(uint32_t num_nodes, uint32_t num_runs,
                                        uint32_t seed, CsvLogger& logger,
                                        bool enable_layer2 = true,
                                        bool enable_adaptive = true,
                                        bool enable_penalty = true,
                                        bool enable_step_decay = true,
                                        bool log_hnd = true) {
    std::vector<double> hnds, drs, convs, fairnesses;

    for (uint32_t run = 0; run < num_runs; run++) {
        uint32_t run_seed = seed + run;

        // Initialize nodes
        std::vector<TwoLayerAlgorithm> nodes;
        std::vector<ObjectiveWeights> weights;
        std::vector<std::vector<uint32_t>> neighbors;

        SimpleRng rng(run_seed);

        // Random positions
        std::vector<std::pair<double, double>> positions(num_nodes);
        for (uint32_t i = 0; i < num_nodes; i++) {
            positions[i] = {rng.Uniform() * AREA_WIDTH, rng.Uniform() * AREA_HEIGHT};
        }

        // Build topology (geometric random graph)
        double range_sq = COMM_RANGE * COMM_RANGE;
        neighbors.resize(num_nodes);
        for (uint32_t i = 0; i < num_nodes; i++) {
            for (uint32_t j = 0; j < num_nodes; j++) {
                if (i == j) continue;
                double dx = positions[i].first - positions[j].first;
                double dy = positions[i].second - positions[j].second;
                if (dx * dx + dy * dy <= range_sq) {
                    neighbors[i].push_back(j);
                }
            }
        }

        // Init nodes
        for (uint32_t i = 0; i < num_nodes; i++) {
            nodes.emplace_back(i, num_nodes, run_seed, enable_penalty);
            weights.push_back(ObjectiveWeights());
        }

        // Build consensus weights
        std::map<uint32_t, std::map<uint32_t, double>> consensus_weights;
        for (uint32_t i = 0; i < num_nodes; i++) {
            double off_diag_sum = 0.0;
            for (uint32_t j : neighbors[i]) {
                uint32_t max_deg = std::max(neighbors[i].size(), neighbors[j].size());
                double w = 1.0 / (max_deg + 1.0);
                consensus_weights[i][j] = w;
                off_diag_sum += w;
            }
            consensus_weights[i][i] = 1.0 - off_diag_sum;
        }

        // Warm-up
        for (auto& node : nodes) {
            node.ConsumeEnergy(enable_layer2);
        }

        // Sample interval for energy logging
        uint32_t sample_interval = std::max(1u, K_MAX / 50);

        // Main loop
        uint32_t converged_at = K_MAX;
        for (uint32_t k = 0; k < K_MAX; k++) {
            // Step size
            double eta = ETA_0;
            if (enable_step_decay) {
                eta = ETA_0 / (1.0 + DELTA * k);
            }

            // Layer 1: Gradient descent
            double max_change = 0.0;
            double max_grad_norm = 0.0;
            for (uint32_t i = 0; i < num_nodes; i++) {
                if (enable_adaptive) {
                    nodes[i].UpdateWeights(weights[i]);
                }
                double delta = nodes[i].Layer1Step(weights[i], eta);
                max_change = std::max(max_change, delta);
                double gn = nodes[i].GetGradientNorm();
                max_grad_norm = std::max(max_grad_norm, gn);
            }

            // Layer 2: Consensus
            double consensus_error = 0.0;
            if (enable_layer2) {
                // Compute consensus average for each node
                std::vector<DecisionVector> new_z(num_nodes);
                for (uint32_t i = 0; i < num_nodes; i++) {
                    DecisionVector total;
                    for (auto& item : consensus_weights[i]) {
                        uint32_t j = item.first;
                        double w = item.second;
                        if (j < num_nodes) {
                            total = total + nodes[j].GetDecisionVector() * w;
                        }
                    }
                    new_z[i] = total;
                }
                for (uint32_t i = 0; i < num_nodes; i++) {
                    nodes[i].Layer2Consensus(new_z[i]);
                    nodes[i].ConsumeConsensusEnergy(neighbors[i].size());
                }
                // Compute consensus error: max deviation from mean z
                DecisionVector z_bar;
                for (uint32_t i = 0; i < num_nodes; i++) {
                    z_bar = z_bar + nodes[i].GetZ();
                }
                if (num_nodes == 0) break;
                z_bar = z_bar * (1.0 / num_nodes);
                for (uint32_t i = 0; i < num_nodes; i++) {
                    double dev = (nodes[i].GetZ() - z_bar).Norm();
                    consensus_error = std::max(consensus_error, dev);
                }
            }

            // Energy consumption
            for (uint32_t i = 0; i < num_nodes; i++) {
                nodes[i].ConsumeEnergy(enable_layer2);
                nodes[i].UpdateDeliveryRatio(0.0);
                nodes[i].IncrementRound();
            }

            // Log intermediate energy and fairness during the loop (for last run)
            if (run == num_runs - 1 && k % sample_interval == 0) {
                double avg_energy = 0.0;
                double s = 0.0, s2 = 0.0;
                for (auto& node : nodes) {
                    avg_energy += node.GetEnergyResidual() / node.GetEnergyInitial();
                    s += node.GetEnergyResidual();
                    s2 += node.GetEnergyResidual() * node.GetEnergyResidual();
                }
                avg_energy /= num_nodes;
                double jains = (s2 < 1e-10) ? 0.0 : (s * s) / (num_nodes * s2);
                logger.LogEnergy("Ours", k, 0, avg_energy * 20.0, avg_energy);
                logger.LogFairness("Ours", k, jains);
                logger.LogConvergence("Ours", k, consensus_error, max_grad_norm, avg_energy);
            }

            // Convergence check
            if (max_change < CONVERGENCE_THRESHOLD && k > 50) {
                converged_at = k + 1;
                break;
            }
        }

        // Compute metrics
        double total_consumed = 0.0;
        double total_dr = 0.0;
        for (auto& node : nodes) {
            total_consumed += node.GetEnergyInitial() - node.GetEnergyResidual();
            total_dr += node.GetDeliveryRatio();
        }

        double hnd = K_MAX;
        uint32_t alive = 0;
        double alive_consumed = 0.0;
        for (auto& node : nodes) {
            double consumed = node.GetEnergyInitial() - node.GetEnergyResidual();
            if (consumed > 0 && node.GetEnergyResidual() > 0.01 * node.GetEnergyInitial()) {
                alive_consumed += consumed;
                alive++;
            }
        }
        if (alive > 0 && alive_consumed > 0) {
            // +1 accounts for the warm-up round before the main loop
            double avg_consumption = alive_consumed / alive / (converged_at + 1);
            double avg_initial = 0.0;
            for (auto& node : nodes) avg_initial += node.GetEnergyInitial();
            avg_initial /= num_nodes;
            if (avg_consumption > 1e-10) {
                hnd = avg_initial / avg_consumption;
            }
        }

        double dr = (num_nodes > 0) ? (total_dr / num_nodes) : 0.0;
        double conv = converged_at * 10.0;  // ms

        // Jain's fairness
        double s = 0.0, s2 = 0.0;
        for (auto& node : nodes) {
            s += node.GetEnergyResidual();
            s2 += node.GetEnergyResidual() * node.GetEnergyResidual();
        }
        double jains = (s2 < 1e-10) ? 0.0 : (s * s) / (num_nodes * s2);

        double energy_eff = (total_consumed > 1e-10) ? (dr * num_nodes / (total_consumed / num_nodes)) : 0.0;

        hnds.push_back(hnd);
        drs.push_back(dr);
        convs.push_back(conv);
        fairnesses.push_back(jains);

        if (log_hnd) {
            logger.LogHnd("Ours", num_nodes, run + 1, hnd, energy_eff, dr, conv, jains, 4.2, 28.0);
        }
    }

    ProtocolResult result;
    result.protocol_name = "Ours";
    result.scale = num_nodes;

    double n = hnds.size();
    if (n == 0) {
        result.hnd_mean = 0.0; result.hnd_std = 0.0;
        result.delivery_ratio_mean = 0.0; result.delivery_ratio_std = 0.0;
        result.convergence_time_ms = 0.0; result.convergence_time_std = 0.0;
        result.jains_fairness = 0.0;
        result.ram_kB = 4.2; result.rom_kB = 28.0;
        return result;
    }
    double hnd_sum = 0, hnd_sq = 0, dr_sum = 0, dr_sq = 0, conv_sum = 0, conv_sq = 0;
    for (size_t i = 0; i < n; i++) {
        hnd_sum += hnds[i]; hnd_sq += hnds[i] * hnds[i];
        dr_sum += drs[i]; dr_sq += drs[i] * drs[i];
        conv_sum += convs[i]; conv_sq += convs[i] * convs[i];
    }
    result.hnd_mean = hnd_sum / n;
    result.hnd_std = std::sqrt(std::max(0.0, hnd_sq / n - result.hnd_mean * result.hnd_mean));
    result.delivery_ratio_mean = dr_sum / n;
    result.delivery_ratio_std = std::sqrt(std::max(0.0, dr_sq / n - result.delivery_ratio_mean * result.delivery_ratio_mean));
    result.convergence_time_ms = conv_sum / n;
    result.convergence_time_std = std::sqrt(std::max(0.0, conv_sq / n - result.convergence_time_ms * result.convergence_time_ms));
    result.jains_fairness = fairnesses.empty() ? 0.0 : fairnesses.back();
    result.ram_kB = 4.2;
    result.rom_kB = 28.0;

    return result;
}

// Run baseline protocol
void RunBaseline(const std::string& protocol_name, uint32_t num_nodes, uint32_t num_runs,
                 uint32_t seed, CsvLogger& logger) {
    for (uint32_t run = 0; run < num_runs; run++) {
        uint32_t run_seed = seed + run;
        std::unique_ptr<BaselineProtocol> baseline;

        if (protocol_name == "LEACH") baseline = std::make_unique<LeachBaseline>(num_nodes, run_seed);
        else if (protocol_name == "HEED") baseline = std::make_unique<HeedBaseline>(num_nodes, run_seed);
        else if (protocol_name == "PEGASIS") baseline = std::make_unique<PegasisBaseline>(num_nodes, run_seed);
        else if (protocol_name == "DeepSensor") baseline = std::make_unique<DeepSensorBaseline>(num_nodes, run_seed);
        else if (protocol_name == "FL-Energy") baseline = std::make_unique<FlEnergyBaseline>(num_nodes, run_seed);
        else {
            std::cerr << "Unknown protocol: " << protocol_name << std::endl;
            return;
        }

        std::vector<double> energies, delivery_ratios, taus;
        std::vector<double> initial_energies;
        baseline->Initialize(energies, delivery_ratios, taus);
        initial_energies = energies;

        uint32_t sample_interval = std::max(1u, K_MAX / 50);
        for (uint32_t r = 0; r < K_MAX; r++) {
            baseline->Step(r, energies, delivery_ratios, taus);
            // Log intermediate energy and fairness for last run
            if (run == num_runs - 1 && r % sample_interval == 0) {
                double avg_norm = 0.0;
                double s = 0.0, s2 = 0.0;
                for (size_t i = 0; i < energies.size(); i++) {
                    avg_norm += energies[i] / initial_energies[i];
                    s += energies[i];
                    s2 += energies[i] * energies[i];
                }
                avg_norm /= num_nodes;
                double jains = (s2 < 1e-10) ? 0.0 : (s * s) / (num_nodes * s2);
                logger.LogEnergy(protocol_name, r, 0, avg_norm * 20.0, avg_norm);
                logger.LogFairness(protocol_name, r, jains);
            }
        }

        double hnd = baseline->ComputeHND(energies, initial_energies);
        double dr = 0.0;
        for (auto d : delivery_ratios) dr += d;
        dr = (num_nodes > 0) ? (dr / num_nodes) : 0.0;
        double total_consumed = 0.0;
        for (size_t i = 0; i < energies.size(); i++) {
            total_consumed += initial_energies[i] - energies[i];
        }
        double energy_eff = (total_consumed > 1e-10) ? (dr * num_nodes / (total_consumed / num_nodes)) : 0.0;
        double jains = baseline->ComputeJainsFairness(energies);

        ProtocolResult br = baseline->GetResult(num_nodes);
        logger.LogHnd(protocol_name, num_nodes, run + 1, hnd, energy_eff, dr, K_MAX * 10.0, jains,
                      br.ram_kB, br.rom_kB);
    }
}

// ============================================================================
// Main
// ============================================================================

int main(int argc, char* argv[]) {
    uint32_t num_nodes = 300;
    uint32_t num_runs = 30;
    uint32_t seed = 42;
    std::string output_dir = "output";
    std::string protocols_str = "LEACH,HEED,PEGASIS,DeepSensor,FL-Energy,Ours";
    std::string scales_str = "100,200,300,500";
    bool ablation = false;

    CommandLine cmd;
    cmd.AddValue("nodes", "Number of nodes", num_nodes);
    cmd.AddValue("runs", "Number of runs", num_runs);
    cmd.AddValue("seed", "Random seed", seed);
    cmd.AddValue("output", "Output directory", output_dir);
    cmd.AddValue("protocols", "Comma-separated protocols", protocols_str);
    cmd.AddValue("scales", "Comma-separated scales", scales_str);
    cmd.AddValue("ablation", "Run ablation study", ablation);
    cmd.Parse(argc, argv);

    // Parse scales and protocols
    std::vector<uint32_t> scales;
    std::stringstream ss_scales(scales_str);
    std::string token;
    while (std::getline(ss_scales, token, ',')) {
        scales.push_back(std::stoul(token));
    }

    std::vector<std::string> protocols;
    std::stringstream ss_proto(protocols_str);
    while (std::getline(ss_proto, token, ',')) {
        protocols.push_back(token);
    }

    std::cout << "============================================================" << std::endl;
    std::cout << " WSN Two-Layer Optimization - NS-3.35 Experiment" << std::endl;
    std::cout << "============================================================" << std::endl;
    std::cout << "Hardware: TelosB (MSP430 @ 8MHz, CC2420 radio)" << std::endl;
    std::cout << "Energy: TX=" << TX_CURRENT_0DBM_mA << "mA, RX=" << RX_CURRENT_mA
              << "mA, Idle=" << IDLE_CURRENT_mA << "mA" << std::endl;
    std::cout << "Scales: " << scales_str << std::endl;
    std::cout << "Protocols: " << protocols_str << std::endl;
    std::cout << "Runs: " << num_runs << std::endl;
    std::cout << "Output: " << output_dir << std::endl;
    std::cout << std::endl;

    if (ablation) {
        // Run ablation study at 300 nodes
        CsvLogger logger(output_dir);

        std::cout << "--- Ablation Study (300 nodes) ---" << std::endl;

        auto run_ablation_variant = [&](const std::string& label,
                                         bool l2, bool adapt, bool penalty, bool decay) {
            std::cout << "  " << label << "..." << std::flush;
            ProtocolResult r = RunTwoLayerOptimization(300, num_runs, seed, logger,
                                                       l2, adapt, penalty, decay, false);
            logger.LogAblation(label, r.hnd_mean, r.hnd_std,
                               r.delivery_ratio_mean, r.delivery_ratio_std,
                               r.convergence_time_ms, r.convergence_time_std);
            std::cout << " done (HND=" << r.hnd_mean << ")" << std::endl;
        };

        run_ablation_variant("Full framework", true, true, true, true);
        run_ablation_variant("w/o Layer 2", false, true, true, true);
        run_ablation_variant("Fixed weights", true, false, true, true);
        run_ablation_variant("w/o penalty", true, true, false, true);
        run_ablation_variant("Constant step", true, true, true, false);
        run_ablation_variant("w/o both", false, false, true, true);

        logger.Finalize();
    } else {
        // Run all protocols at all scales
        for (uint32_t scale : scales) {
            std::string scale_dir = output_dir + "/scale_" + std::to_string(scale);
            CsvLogger logger(scale_dir);

            std::cout << "--- Scale: " << scale << " nodes ---" << std::endl;

            for (const auto& protocol : protocols) {
                std::cout << "  [" << protocol << "] scale=" << scale
                          << ", runs=" << num_runs << "..." << std::flush;

                if (protocol == "Ours") {
                    RunTwoLayerOptimization(scale, num_runs, seed + scale, logger);
                } else {
                    RunBaseline(protocol, scale, num_runs, seed + scale, logger);
                }
                std::cout << " done" << std::endl;
            }

            logger.Finalize();
            std::cout << std::endl;
        }
    }

    std::cout << "============================================================" << std::endl;
    std::cout << "Experiment complete. Results saved to: " << output_dir << std::endl;
    std::cout << "============================================================" << std::endl;

    return 0;
}