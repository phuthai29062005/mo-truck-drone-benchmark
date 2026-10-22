# Comparison Algorithms

## Overview

We compare our proposed method against 8 algorithms spanning three categories:
generic multi-objective metaheuristics, problem-specific heuristics from the
truck-drone routing literature, and matheuristic approaches.

## Algorithm list

### Category 1: Generic multi-objective metaheuristics (baselines)

| # | Algorithm | Reference | Venue | Year |
|---|-----------|-----------|-------|------|
| 1 | **NSGA-II** | Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. "A fast and elitist multiobjective genetic algorithm: NSGA-II" | IEEE Trans. Evolutionary Computation, 6(2), 182-197 | 2002 |
| 2 | **NSGA-III** | Deb, K., & Jain, H. "An evolutionary many-objective optimization algorithm using reference-point-based nondominated sorting approach, Part I" | IEEE Trans. Evolutionary Computation, 18(4), 577-601 | 2014 |
| 3 | **MOEA/D** | Zhang, Q., & Li, H. "MOEA/D: A multiobjective evolutionary algorithm based on decomposition" | IEEE Trans. Evolutionary Computation, 11(6), 712-731 | 2007 |

These three are standard baselines in any multi-objective optimization paper.
They must be adapted to our problem with problem-specific operators (encoding, decoding, repair).

### Category 2: Truck-drone routing heuristics

| # | Algorithm | Reference | Venue | Year |
|---|-----------|-----------|-------|------|
| 4 | **GA-SA+NDS** | Ge, H., Chen, S., Chen, G., Chen, W. "Multi-objective optimization for the vehicle-drone routing problem with time windows" | Transportation Research Part E: Logistics and Transportation Review | 2025 |
| 5 | **HGA** | Ha, Q.M., Deville, Y., Pham, Q.D., & Ha, M.H. "A hybrid genetic algorithm for the traveling salesman problem with drone" | Journal of Heuristics, 26, 219-247 | 2020 |
| 6 | **ALNS** | Sacramento, D., Pisinger, D., & Ropke, S. "An adaptive large neighborhood search metaheuristic for the vehicle routing problem with drones" | Transportation Research Part C: Emerging Technologies, 102, 289-315 | 2019 |
| 7 | **HVNS+DP** | Ren, K., Yin, Y., Wang, S., & Chen, Z. "A branch-and-price algorithm for the vehicle routing problem with drones and multiple visits" | European Journal of Operational Research | 2024 |

Notes:
- **GA-SA+NDS**: GA + simulated annealing hybrid with non-dominated sorting. Same problem class (multi-objective truck-drone with TW).
- **HGA**: Hybrid genetic algorithm for TSP-D. Must be extended to handle TW, partial charging, and multi-objective.
- **ALNS**: Adaptive large neighborhood search for VRP-D. Must be extended with MO wrapper.
- **HVNS+DP**: Hybrid VNS with DP pricing. Single-objective but structurally relevant.

### Category 3: Multi-objective approach from related problems

| # | Algorithm | Reference | Venue | Year |
|---|-----------|-----------|-------|------|
| 8 | **BOA-KS** | Multi-objective butterfly optimization with knapsack-based selection | Expert Systems with Applications (ESWA) | 2024 |

## Implementation notes for adapting algorithms

### Adapting single-objective algorithms to multi-objective

For algorithms 5, 6, 7 (originally single-objective):
- Wrap with **epsilon-constraint**: fix makespan <= T_bar, minimize energy. Sweep T_bar over a grid.
- Or wrap with **weighted-sum scalarization**: min lambda * T_max + (1-lambda) * E_system. Sweep lambda in [0, 1].
- Collect all solutions across sweeps, filter non-dominated.

### Adapting to our problem specifics

All algorithms need these adaptations:
1. **Drone assignment**: decide which customers are drone-served vs truck-served
2. **Flexible sites**: allow insertion of flexible sites as launch/recovery points
3. **Partial charging**: schedule charging at stops and during pure-truck segments
4. **Battery feasibility**: check B_{k,h} >= E^D + B_min before each sortie
5. **Synchronization**: compute hover/wait times at recovery nodes
6. **Soft time windows**: compute tardiness, enforce L_total <= eps_L
7. **Forced drone (variant B)**: ensure forced_drone customers are NOT in truck routes

### Suggested encoding (for GA-based methods)

A two-layer chromosome:
- **Layer 1 (permutation pi)**: visit order of all customers (giant tour)
- **Layer 2 (binary b)**: for each drone-eligible customer, 0 = truck, 1 = drone
- **Decoding**: split giant tour into truck routes; assign drone customers to sorties; schedule charging; compute objectives

### Operator library

Destroy operators: random removal, worst removal (by tardiness contribution), route removal, drone-related removal, time-window removal.

Repair operators: greedy insertion (by min objective increase), regret-k insertion, drone-first insertion.

Local search: 2-opt, or-opt, swap (within/between routes), drone toggle (switch truck<->drone), flexible-site insertion/removal.

## Experimental setup

| Parameter | Value |
|-----------|-------|
| Runs per instance | 30 (different random seeds) |
| Max evaluations | 500,000 per run |
| Time limit | 600 seconds per run (100-customer instances) |
| Population size (GA-based) | 100 |
| Number of pairs M | 5 |
| Tardiness limit eps_L | 50.0 |
| Statistical test | Wilcoxon rank-sum, significance level 0.05 |

## How to submit results

1. Run your algorithm 30 times on each of the 112 instances
2. Save results in the format specified in `output_format.md`
3. Use the evaluation script to compute metrics
