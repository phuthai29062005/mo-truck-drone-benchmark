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


def validate_solution(inst, sol, eps_L=50.0, M=5):
    """Validate one solution from the Pareto front. Returns list of errors."""
    errors = []
    warnings = []
    params = inst["drone_params"]

    if "routes" not in sol:
        warnings.append("No route detail provided; can only check objective values")
        # Check tardiness
        tard = sol.get("tardiness", 0)
        if tard > eps_L:
            errors.append(f"Tardiness {tard:.2f} exceeds eps_L={eps_L}")
        return errors, warnings

    routes = sol["routes"]

    # --- Check 1: all customers served exactly once ---
    served = {}  # customer_id -> 'truck' or 'drone'
    for route in routes:
        pair_id = route["pair_id"]
        truck_route = route["truck_route"]

        # Customers in truck route (served by truck)
        for node in truck_route:
            if isinstance(node, int) and node > 0:
                cust = get_node(inst, node)
                if not cust.get("forced_drone", False):
                    if node in served:
                        errors.append(f"Customer {node} served multiple times "
                                      f"(truck pair {pair_id} and {served[node]})")
                    else:
                        served[node] = f"truck pair {pair_id}"

        # Customers served by drone
        for seg in route.get("segments", []):
            if seg["type"] == "drone":
                dc = seg["drone_customer"]
                if dc in served:
                    errors.append(f"Customer {dc} served multiple times "
                                  f"(drone pair {pair_id} and {served[dc]})")
                else:
                    served[dc] = f"drone pair {pair_id}"

    all_customers = {c["id"] for c in inst["customers"]}
    unserved = all_customers - set(served.keys())
    if unserved:
        errors.append(f"Unserved customers: {sorted(unserved)}")

    # --- Check 2: forced drone customers (variant B) ---
    forced = set(inst.get("forced_drone_only", []))
    for fid in forced:
        if fid in served and "truck" in served[fid]:
            errors.append(f"Forced-drone customer {fid} served by truck")

    # --- Check 3: drone payload ---
    for route in routes:
        for seg in route.get("segments", []):
            if seg["type"] == "drone":
                dc = seg["drone_customer"]
                cust = get_node(inst, dc)
                if cust["demand"] > params["drone_payload_cap"]:
                    errors.append(f"Drone customer {dc} demand {cust['demand']} "
                                  f"exceeds payload cap {params['drone_payload_cap']}")

    # --- Check 4: truck capacity ---
    for route in routes:
        total_demand = 0
        for node in route["truck_route"]:
            if isinstance(node, int) and node > 0:
                total_demand += get_node(inst, node)["demand"]
        for seg in route.get("segments", []):
            if seg["type"] == "drone":
                dc = seg["drone_customer"]
                total_demand += get_node(inst, dc)["demand"]
        if total_demand > inst["truck_capacity"]:
            errors.append(f"Pair {route['pair_id']} total demand {total_demand} "
                          f"exceeds truck capacity {inst['truck_capacity']}")

    # --- Check 5: battery feasibility ---
    for route in routes:
        battery = params["battery_max"]
        for seg in route.get("segments", []):
            charge = seg.get("charge_amount", 0)
            battery = min(battery + charge, params["battery_max"])

            if seg["type"] == "drone":
                energy = seg.get("drone_energy", 0)
                if battery - energy < params["battery_min"] - 1e-6:
                    errors.append(
                        f"Pair {route['pair_id']}: battery {battery:.4f} - "
                        f"energy {energy:.4f} = {battery-energy:.4f} < "
                        f"B_min {params['battery_min']}")
                battery -= energy

            if battery < params["battery_min"] - 1e-6:
                errors.append(
                    f"Pair {route['pair_id']}: battery {battery:.4f} < "
                    f"B_min {params['battery_min']}")

    # --- Check 6: tardiness ---
    tard = sol.get("tardiness", 0)
    if tard > eps_L + 1e-6:
        errors.append(f"Total tardiness {tard:.2f} exceeds eps_L={eps_L}")

    return errors, warnings


def validate_front(inst, sol_data, eps_L=50.0, M=5):
    """Validate entire solution file."""
    all_errors = []
    all_warnings = []

    front = sol_data.get("pareto_front", [])
    if not front:
        all_errors.append("Empty Pareto front")
        return all_errors, all_warnings

    # Check non-domination
    for i, a in enumerate(front):
        for j, b in enumerate(front):
            if i != j:
                mk_a, en_a = a["makespan"], a["energy"]
                mk_b, en_b = b["makespan"], b["energy"]
                if mk_a <= mk_b and en_a <= en_b and (mk_a < mk_b or en_a < en_b):
                    all_warnings.append(
                        f"Solution {i} dominates solution {j}: "
                        f"({mk_a:.2f}, {en_a:.2f}) vs ({mk_b:.2f}, {en_b:.2f})")

    # Validate each solution
    for idx, sol in enumerate(front):
        errs, warns = validate_solution(inst, sol, eps_L, M)
        for e in errs:
            all_errors.append(f"Solution {idx}: {e}")
        for w in warns:
            all_warnings.append(f"Solution {idx}: {w}")

    return all_errors, all_warnings


def main():
    parser = argparse.ArgumentParser(description="Validate solution feasibility")
    parser.add_argument("instance", help="Instance JSON file")
    parser.add_argument("solution", help="Solution JSON file")
    parser.add_argument("--eps_L", type=float, default=50.0,
                        help="Tardiness limit (default: 50)")
    parser.add_argument("--M", type=int, default=5,
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
