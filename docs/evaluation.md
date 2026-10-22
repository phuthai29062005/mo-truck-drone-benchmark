# Evaluation Protocol

## Metrics

### Primary metrics

| Metric | Symbol | Description | Better |
|--------|--------|-------------|--------|
| **Hypervolume** | HV | Volume dominated by the front, bounded by reference point | Higher |
| **Inverted Generational Distance+** | IGD+ | Average distance from reference front to obtained front (Ishibuchi et al. 2015) | Lower |
| **Epsilon indicator** | I_eps | Minimum factor to shift obtained front to dominate reference | Lower |

### Secondary metrics

| Metric | Description | Better |
|--------|-------------|--------|
| **#ND** | Number of non-dominated solutions in the front | Context-dependent |
| **Spacing** | Uniformity of the front distribution | Lower |
| **Runtime** | Wall-clock time in seconds | Lower |
| **#Evaluations** | Total solution evaluations | Lower |
| **Feasibility rate** | Fraction of 30 runs producing at least 1 feasible solution | Higher |

### Reference point for HV

The reference point is computed per instance:

```
r = (1.1 * T_max_worst, 1.1 * E_max_worst)
```

where T_max_worst and E_max_worst are the worst (largest) objective values across ALL algorithms and ALL runs on that instance. This ensures all algorithms use the same reference point.

### Reference front for IGD+

The reference Pareto front is the union of all non-dominated solutions across ALL algorithms and ALL 30 runs on that instance. This is the best-known front for that instance.

## Normalization

Before computing metrics, objectives are normalized to [0, 1] using the range of the reference front:

```
f_1_norm = (f_1 - f_1_min) / (f_1_max - f_1_min)
f_2_norm = (f_2 - f_2_min) / (f_2_max - f_2_min)
```

where f_min, f_max come from the reference front (union of all algorithms).

## Statistical testing

1. Run each algorithm 30 times per instance (different random seeds)
2. Compute HV (or IGD+) for each run
3. Compare algorithms pairwise using **Wilcoxon rank-sum test** (alpha = 0.05)
4. Report win/tie/loss counts across all instances
5. Use **Friedman test** for overall ranking across all instances

## Reporting format

### Per-instance table

| Instance | Metric | Algo1 (mean +/- std) | Algo2 | ... | Best |
|----------|--------|----------------------|-------|-----|------|
| C101_A   | HV     | 0.85 +/- 0.02        | 0.82  | ... | Algo1 |
| C101_A   | IGD+   | 0.05 +/- 0.01        | 0.08  | ... | Algo1 |

### Aggregated table (by category)

| Category | Metric | Algo1 | Algo2 | ... |
|----------|--------|-------|-------|-----|
| C1       | HV avg | 0.83  | 0.79  | ... |
| R1       | HV avg | 0.78  | 0.75  | ... |

### Win/tie/loss table

| Algo1 vs | Win | Tie | Loss | (based on Wilcoxon, HV) |
|----------|-----|-----|------|-------------------------|
| NSGA-II  | 95  | 10  | 7    |                         |
| NSGA-III | 88  | 15  | 9    |                         |

## Convergence analysis

Plot the HV vs. number of evaluations (at intervals of 10,000 evaluations) for a representative instance (e.g., R101_A) to show convergence speed.

## Sensitivity analysis

Test with:
- eps_L in {10, 25, 50, 100, infinity}: effect of tardiness strictness
- M in {3, 5, 7}: effect of fleet size
- On 3 representative instances: one from C1 (clustered/tight), one from R2 (random/wide), one from RC1 (mixed/tight)
