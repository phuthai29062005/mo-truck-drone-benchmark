"""Run one baseline or a reproducible batch; see --help."""

import argparse
import json
from pathlib import Path

from .algorithms import optimize
from .model import Problem


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instances", nargs="+", type=Path, help="Instance files or directories")
    parser.add_argument("--algorithm", choices=("NSGA-II", "NSGA-III", "MOEA/D", "all"), default="all")
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--evaluations", type=int, default=500000)
    parser.add_argument("--time-limit", type=float, default=600)
    parser.add_argument("--M", type=int, default=5)
    parser.add_argument("--eps-L", "--eps_L", dest="eps_L", type=float, default=50)
    parser.add_argument("--truck-capacity", type=float, help="Explicit experimental override; does not edit the instance")
    parser.add_argument("--eta-c", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42, help="First seed; subsequent runs increment it")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    paths = sorted({f for p in args.instances for f in (sorted(p.glob("*.json")) if p.is_dir() else [p])})
    if not paths:
        parser.error("No instance files found")
    algorithms = ("NSGA-II", "NSGA-III", "MOEA/D") if args.algorithm == "all" else (args.algorithm,)
    any_failed = False
    for path in paths:
        with path.open() as f:
            instance = json.load(f)
        try:
            problem = Problem(instance, args.M, args.eps_L, args.truck_capacity, args.eta_c)
            for algorithm in algorithms:
                for run in range(1, args.runs+1):
                    seed = args.seed + run - 1
                    result = optimize(problem, algorithm, args.population, args.evaluations, args.time_limit, seed)
                    result.update(instance=path.stem, algorithm=algorithm, n_pairs=args.M,
                                  eps_L=args.eps_L, truck_capacity=problem.capacity, eta_c=args.eta_c,
                                  seed=seed, run_id=run,
                                  configuration=dict(population_size=args.population,
                                                     max_evaluations=args.evaluations, time_limit=args.time_limit))
                    folder = args.output_dir / algorithm.replace("/", "_")
                    folder.mkdir(parents=True, exist_ok=True)
                    target = folder / f"{algorithm.replace('/', '_')}_{path.stem}_{run:02d}.json"
                    if target.exists():
                        raise ValueError(f"Output already exists: {target}; choose a different --output-dir")
                    with target.open("w") as f:
                        json.dump(result, f, indent=2, allow_nan=False)
                    print(f"{algorithm} {path.stem} run={run} status={result['status']} "
                          f"ND={len(result['pareto_front'])} evals={result['n_evaluations']} -> {target}")
                    for message in result.get("diagnostics", []):
                        print(f"  {message}")
                    any_failed |= result["status"] != "ok"
        except ValueError as error:
            parser.error(str(error))
    return 2 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
