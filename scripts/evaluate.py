#!/usr/bin/env python3
"""
Evaluate Pareto front quality: HV, IGD+, epsilon indicator.

Usage:
  python evaluate.py solution.json                         # basic stats
  python evaluate.py solution.json --ref reference.json    # HV, IGD+, eps
  python evaluate.py results_dir/ --ref reference.json     # batch mode

Reference front: union of non-dominated points across all algorithms.
Generate with: python evaluate.py --build-ref results_dir/ -o ref.json
"""

import json
import math
import argparse
import os
import sys
from pathlib import Path


# ============================================================
# Pareto utilities
# ============================================================

def dominates(a, b):
    """a dominates b in minimization (both are [f1, f2])."""
    return all(ai <= bi for ai, bi in zip(a, b)) and any(ai < bi for ai, bi in zip(a, b))


def filter_nondominated(points):
    """Return non-dominated subset of points."""
    nd = []
    for p in points:
        if not any(dominates(q, p) for q in points if q is not p):
            nd.append(p)
    return nd


def normalize_front(front, f_min, f_max):
    """Normalize to [0,1] using given bounds."""
    norm = []
    for p in front:
        np_ = []
        for i in range(len(p)):
            r = f_max[i] - f_min[i]
            np_.append((p[i] - f_min[i]) / r if r > 1e-12 else 0.0)
        norm.append(np_)
    return norm


# ============================================================
# Hypervolume (2D exact)
# ============================================================

def hypervolume_2d(front, ref):
    """
    Exact 2D hypervolume.
    front: list of [f1, f2], ref: [r1, r2].
    """
    # Filter points dominated by ref
    pts = [p for p in front if p[0] < ref[0] and p[1] < ref[1]]
    if not pts:
        return 0.0

    # Sort by f1 ascending
    pts.sort(key=lambda p: p[0])

    hv = 0.0
    prev_y = ref[1]
    for p in pts:
        if p[1] < prev_y:
            hv += (ref[0] - p[0]) * (prev_y - p[1])
            prev_y = p[1]
    return hv


# ============================================================
# IGD+ (Ishibuchi et al. 2015)
# ============================================================

def igd_plus(obtained, reference):
    """
    IGD+ from reference to obtained front.
    Uses modified distance: max(obtained_i - ref_i, 0) for each objective.
    """
    if not obtained:
        return float('inf')

    total = 0.0
    for r in reference:
        min_d = float('inf')
        for o in obtained:
            d = math.sqrt(sum(max(oi - ri, 0)**2 for oi, ri in zip(o, r)))
            min_d = min(min_d, d)
        total += min_d
    return total / len(reference)


# ============================================================
# Epsilon indicator (additive)
# ============================================================

def epsilon_indicator(obtained, reference):
    """
    Additive epsilon indicator: min eps such that
    for every ref point r, there exists obtained point o with
    o_i - eps <= r_i for all i.
    """
    if not obtained:
        return float('inf')

    eps = float('-inf')
    for r in reference:
        min_eps_r = float('inf')
        for o in obtained:
            max_diff = max(oi - ri for oi, ri in zip(o, r))
            min_eps_r = min(min_eps_r, max_diff)
        eps = max(eps, min_eps_r)
    return eps


# ============================================================
# Spacing
# ============================================================

def spacing(front):
    """Spacing metric: std of nearest-neighbor distances."""
    if len(front) <= 1:
        return 0.0

    dists = []
    for i, p in enumerate(front):
        min_d = float('inf')
        for j, q in enumerate(front):
            if i != j:
                d = math.sqrt(sum((pi - qi)**2 for pi, qi in zip(p, q)))
                min_d = min(min_d, d)
        dists.append(min_d)

    mean_d = sum(dists) / len(dists)
    var = sum((d - mean_d)**2 for d in dists) / len(dists)
    return math.sqrt(var)


# ============================================================
# Load solution
# ============================================================

def load_solution(path):
    """Load a solution file, return list of [makespan, energy] points."""
    with open(path) as f:
        data = json.load(f)

    points = []
    for sol in data.get("pareto_front", []):
        mk = sol.get("makespan", sol.get("f1"))
        en = sol.get("energy", sol.get("f2"))
        if mk is not None and en is not None:
            points.append([float(mk), float(en)])

    return filter_nondominated(points), data


def load_reference(path):
    """Load reference front."""
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        return [[p[0], p[1]] for p in data]
    elif "pareto_front" in data:
        return [[p["makespan"], p["energy"]] for p in data["pareto_front"]]
    elif "reference_front" in data:
        return [[p[0], p[1]] for p in data["reference_front"]]
    else:
        raise ValueError(f"Cannot parse reference front from {path}")


# ============================================================
# Build reference front
# ============================================================

def build_reference_front(results_dir):
    """Collect all fronts from a results directory, return union ND front."""
    all_points = []
    for root, dirs, files in os.walk(results_dir):
        for fname in files:
            if fname.endswith(".json"):
                try:
                    pts, _ = load_solution(os.path.join(root, fname))
                    all_points.extend(pts)
                except Exception:
                    continue

    return filter_nondominated(all_points)


# ============================================================
# Main
# ============================================================

def evaluate_solution(sol_path, ref_front=None):
    """Evaluate one solution file."""
    front, data = load_solution(sol_path)

    result = {
        "file": str(sol_path),
        "instance": data.get("instance", "unknown"),
        "algorithm": data.get("algorithm", "unknown"),
        "n_solutions": len(front),
        "runtime": data.get("runtime_seconds"),
    }

    if not front:
        result["error"] = "Empty front"
        return result

    # Objective ranges
    f1_vals = [p[0] for p in front]
    f2_vals = [p[1] for p in front]
    result["makespan_range"] = [min(f1_vals), max(f1_vals)]
    result["energy_range"] = [min(f2_vals), max(f2_vals)]
    result["spacing"] = round(spacing(front), 6)

    if ref_front and len(ref_front) > 0:
        # Compute bounds for normalization
        all_pts = front + ref_front
        f_min = [min(p[i] for p in all_pts) for i in range(2)]
        f_max = [max(p[i] for p in all_pts) for i in range(2)]

        norm_front = normalize_front(front, f_min, f_max)
        norm_ref = normalize_front(ref_front, f_min, f_max)

        # HV with ref point (1.1, 1.1) in normalized space
        ref_point = [1.1, 1.1]
        result["HV"] = round(hypervolume_2d(norm_front, ref_point), 6)

        # IGD+
        result["IGD+"] = round(igd_plus(norm_front, norm_ref), 6)

        # Epsilon
        result["epsilon"] = round(epsilon_indicator(norm_front, norm_ref), 6)

    return result


def main():
    parser = argparse.ArgumentParser(description="Evaluate Pareto front quality")
    parser.add_argument("input", help="Solution JSON file or results directory")
    parser.add_argument("--ref", help="Reference front JSON file")
    parser.add_argument("--build-ref", action="store_true",
                        help="Build reference front from input directory")
    parser.add_argument("-o", "--output", help="Output file for reference front")
    args = parser.parse_args()

    if args.build_ref:
        ref = build_reference_front(args.input)
        print(f"Built reference front: {len(ref)} non-dominated points")
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({"reference_front": ref}, f, indent=2)
            print(f"Saved to {args.output}")
        else:
            print(json.dumps(ref[:5], indent=2), "...")
        return

    ref_front = None
    if args.ref:
        ref_front = load_reference(args.ref)
        print(f"Reference front: {len(ref_front)} points")

    if os.path.isdir(args.input):
        results = []
        for fname in sorted(os.listdir(args.input)):
            if fname.endswith(".json"):
                r = evaluate_solution(os.path.join(args.input, fname), ref_front)
                results.append(r)
                print(f"  {r['algorithm']:15s} {r['instance']:12s} "
                      f"#ND={r['n_solutions']:3d} "
                      f"HV={r.get('HV', 'N/A'):>8s}" if isinstance(r.get('HV'), str)
                      else f"  {r['algorithm']:15s} {r['instance']:12s} "
                           f"#ND={r['n_solutions']:3d} "
                           f"HV={r.get('HV', 'N/A')}")
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
    else:
        r = evaluate_solution(args.input, ref_front)
        print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
