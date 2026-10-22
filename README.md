# Multi-objective Truck-Drone Routing Benchmark

**Multi-objective Truck-Drone Routing with Flexible Rendezvous, Partial Charging, and Soft Time Windows**

## Problem overview

- **M** truck-drone pairs; each truck carries exactly one drone
- Each drone sortie serves exactly 1 customer; launch at truck stop h, recover at stop h+1
- Recovery points: depot, customer, or predefined flexible site
- Partial charging: on moving truck (rate rho_m) or while stopped (rate rho_s, costs extra stop time)
- Soft time windows: total weighted tardiness is a constraint (L_total <= eps_L), not an objective
- **Objectives**: minimize makespan T_max AND minimize total system energy E_system
- **Output**: Pareto front approximation

## Repository structure

```
mo-truck-drone-benchmark/
  README.md                    # This file
  docs/
    problem_specification.md   # Full mathematical model (English)
    input_format.md            # JSON input schema with field descriptions
    output_format.md           # Required output format for Pareto front
    algorithms.md              # Comparison algorithms with references
    evaluation.md              # Metrics and evaluation protocol
  instances/                   # 112 benchmark instances (56 base x 2 variants)
    C101_A.json ... RC208_B.json
  scripts/
    evaluate.py                # Compute HV, IGD+, epsilon indicator
    validate_solution.py       # Check feasibility of a solution file
    generate_instances.py      # Instance generator (for reproducibility)
```

## Instances

56 Solomon-style 100-customer instances across 6 categories, each with 2 variants:

| Category | Count | Spatial | Time windows |
|----------|-------|---------|-------------|
| C1 (C101-C109) | 9 | Clustered | Tight |
| C2 (C201-C208) | 8 | Clustered | Wide |
| R1 (R101-R112) | 12 | Random | Tight |
| R2 (R201-R211) | 11 | Random | Wide |
| RC1 (RC101-RC108) | 8 | Mixed | Tight |
| RC2 (RC201-RC208) | 8 | Mixed | Wide |

**Variant A** (natural UAV advantage): all edges exist; truck uses detour factor 1.3x Euclidean, drone flies Euclidean at higher speed (40 vs 30).

**Variant B** (forced UAV): ~15% of customers are truck-inaccessible (drone-only). These are the closest drone-feasible customers to the depot.

## Quick start

1. Pick an instance, e.g., `instances/R101_A.json`
2. Run your algorithm; produce output in the format specified in `docs/output_format.md`
3. Validate: `python scripts/validate_solution.py R101_A.json your_solution.json`
4. Evaluate: `python scripts/evaluate.py --ref reference_front.json your_solution.json`

## Comparison algorithms

See `docs/algorithms.md` for the full list with references.

## Evaluation metrics

See `docs/evaluation.md` for the protocol: HV, IGD+, epsilon indicator, #ND, runtime.

## Citation

If you use this benchmark, please cite:
```
[Paper reference TBD]
```

## License

The benchmark instances and evaluation scripts are released for academic research purposes.
