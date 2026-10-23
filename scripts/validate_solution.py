#!/usr/bin/env python3
"""
Validate a solution file against an instance.

Checks:
  1. All customers served exactly once
  2. Truck capacity respected
  3. Drone payload capacity respected
  4. Drone-only customers (variant B) served by drone
  5. Battery feasibility (B >= B_min at all times)
  6. Time window tardiness within eps_L
  7. Synchronization timing correctness
  8. Non-dominated front (no dominated solutions)

Usage:
  python validate_solution.py instance.json solution.json [--eps_L 50] [--M 5]
"""

import json
import math
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def euclidean(a, b):
    ax, ay = (a["x"], a["y"]) if isinstance(a, dict) else a
    bx, by = (b["x"], b["y"]) if isinstance(b, dict) else b
    return math.sqrt((ax - bx)**2 + (ay - by)**2)


def load_instance(path):
    with open(path) as f:
        return json.load(f)


def load_solution(path):
    with open(path) as f:
        return json.load(f)


def get_node(inst, node_id):
    """Get node coordinates by ID. 0=depot, int=customer, 'Fn'=flexible site."""
    if node_id == 0:
        return inst["depot"]
    if isinstance(node_id, int):
        for c in inst["customers"]:
            if c["id"] == node_id:
                return c
        raise ValueError(f"Customer {node_id} not found")
    if isinstance(node_id, str) and node_id.startswith("F"):
        for fs in inst["flexible_sites"]:
            if fs["id"] == node_id:
                return fs
        raise ValueError(f"Flexible site {node_id} not found")
    raise ValueError(f"Unknown node: {node_id}")


def validate_solution(inst, sol, eps_L=50.0, M=5, truck_capacity=None, eta_c=1.0):
    """Replay complete routes and compare reported values with the model."""
    from truck_drone.model import Problem
    errors, warnings = [], []
    if "routes" not in sol:
        return ["Route detail required to certify feasibility"], warnings
    try:
        problem = Problem(inst, M, eps_L, truck_capacity, eta_c)
        replay = problem.simulate(sol["routes"])
        errors.extend(replay.errors)
        def compare(label, supplied, computed):
            if not isinstance(supplied, (int, float)) or not math.isfinite(supplied) or not math.isclose(supplied, computed, rel_tol=1e-7, abs_tol=1e-6):
                errors.append(f"{label}: reported {supplied}, recomputed {computed}")
        for field in ("makespan", "energy", "tardiness"):
            compare(field, sol.get(field), replay.solution[field])
        if "n_drone_sorties" in sol:
            compare("n_drone_sorties", sol["n_drone_sorties"], replay.solution["n_drone_sorties"])
        for route, computed in zip(sol["routes"], replay.solution["routes"]):
            for seg, expected in zip(route["segments"], computed["segments"]):
                for field in ("depart_time", "arrive_time", "drone_energy", "hover_time",
                              "truck_wait", "battery_before", "battery_after"):
                    if field in seg:
                        compare(f"pair {route['pair_id']} {field}", seg[field], expected[field])
    except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError) as error:
        errors.append(f"Malformed solution/instance: {error}")
    return errors, warnings


def validate_front(inst, sol_data, eps_L=None, M=None, truck_capacity=None, eta_c=None):
    """Validate all points with experiment parameters from file unless overridden."""
    eps_L = sol_data.get("eps_L", 50.0) if eps_L is None else eps_L
    M = sol_data.get("n_pairs", 5) if M is None else M
    truck_capacity = sol_data.get("truck_capacity") if truck_capacity is None else truck_capacity
    eta_c = sol_data.get("eta_c", 1.0) if eta_c is None else eta_c
    errors, warnings = [], []
    front = sol_data.get("pareto_front", [])
    if not front:
        return ["Empty Pareto front"], warnings
    if sol_data.get("status", "ok") != "ok":
        errors.append("Non-success status cannot contain a feasible front")
    for idx, sol in enumerate(front):
        errs, warns = validate_solution(inst, sol, eps_L, M, truck_capacity, eta_c)
        errors.extend(f"Solution {idx}: {e}" for e in errs)
        warnings.extend(f"Solution {idx}: {w}" for w in warns)
    for i, a in enumerate(front):
        for j, b in enumerate(front):
            if i != j and all(isinstance(x.get(k), (int, float)) for x in (a, b) for k in ("makespan", "energy")):
                if a["makespan"] <= b["makespan"] and a["energy"] <= b["energy"] and (a["makespan"] < b["makespan"] or a["energy"] < b["energy"]):
                    errors.append(f"Solution {i} dominates solution {j}")
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate solution feasibility")
    parser.add_argument("instance", help="Instance JSON file")
    parser.add_argument("solution", help="Solution JSON file")
    parser.add_argument("--eps_L", type=float, default=None,
                        help="Tardiness limit (default: 50)")
    parser.add_argument("--M", type=int, default=None,
                        help="Number of truck-drone pairs (default: 5)")
    args = parser.parse_args()

    inst = load_instance(args.instance)
    sol_data = load_solution(args.solution)

    print(f"Instance: {inst['name']} ({inst.get('variant', 'unknown')})")
    print(f"Algorithm: {sol_data.get('algorithm', 'unknown')}")
    print(f"Front size: {len(sol_data.get('pareto_front', []))}")
    print()

    errors, warnings = validate_front(inst, sol_data, args.eps_L, args.M)

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  [W] {w}")
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  [E] {e}")
        print()
        print("RESULT: INVALID")
        sys.exit(1)
    else:
        print("RESULT: VALID")
        sys.exit(0)


if __name__ == "__main__":
    main()
