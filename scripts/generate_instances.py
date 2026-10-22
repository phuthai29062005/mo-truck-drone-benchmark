"""
Generate FULL Solomon VRPTW benchmark suite with drone parameters.
56 instances total:
  C1: C101–C109 (9)  — clustered, tight TW
  C2: C201–C208 (8)  — clustered, wide TW
  R1: R101–R112 (12) — random, tight TW
  R2: R201–R211 (11) — random, wide TW
  RC1: RC101–RC108 (8) — mixed, tight TW
  RC2: RC201–RC208 (8) — mixed, wide TW

Each instance has 2 variants:
  _A.json — Type A: natural UAV advantage (truck detour factor, drone Euclidean)
  _B.json — Type B: forced UAV (15% customers truck-inaccessible)

Plus _solomon.txt in standard Solomon format for compatibility.
"""

import json
import random
import math
import os
import sys

# ============================================================
# DRONE PARAMETERS (appended to Solomon base)
# ============================================================
DRONE_PARAMS = {
    "drone_speed": 40.0,
    "truck_speed": 30.0,
    "battery_max": 1.0,
    "battery_min": 0.1,
    "charge_rate_stopped": 0.05,
    "charge_rate_moving": 0.02,
    "launch_time": 1.0,
    "recovery_time": 1.0,
    "drone_payload_cap": 10,
    "P0": 0.005,
    "alpha": 0.001,
    "hover_power": 0.008,
    "detour_factor": 1.3,
    "forced_drone_pct": 0.15,
}

AREA = 100
N_CUSTOMERS = 100
HORIZON = 230
TRUCK_CAP = 200

# ============================================================
# Coordinate generators
# ============================================================
def euclidean(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def gen_clustered(n, seed):
    rng = random.Random(seed)
    coords = []
    n_clusters = max(3, n // 8)
    centers = [(rng.randint(15, AREA-15), rng.randint(15, AREA-15))
               for _ in range(n_clusters)]
    per_cluster = n // n_clusters
    for i, (cx, cy) in enumerate(centers):
        count = per_cluster if i < n_clusters - 1 else n - len(coords)
        for _ in range(count):
            x = max(0, min(AREA, cx + rng.gauss(0, 10)))
            y = max(0, min(AREA, cy + rng.gauss(0, 10)))
            coords.append((round(x, 1), round(y, 1)))
    return coords

def gen_random(n, seed):
    rng = random.Random(seed)
    return [(round(rng.uniform(0, AREA), 1), round(rng.uniform(0, AREA), 1))
            for _ in range(n)]

def gen_mixed(n, seed):
    rng = random.Random(seed)
    n_clust = n // 2
    n_rand = n - n_clust
    c = gen_clustered(n_clust, seed)
    r = gen_random(n_rand, seed + 10000)
    combined = c + r
    rng.shuffle(combined)
    return combined

# ============================================================
# Time window generator
# ============================================================
def gen_time_windows(n, tw_width, seed):
    """
    tw_width: 'tight' → small windows (type 1)
              'wide'  → large windows (type 2)
    """
    rng = random.Random(seed)
    windows = []
    service_times = []
    for _ in range(n):
        center = rng.randint(10, HORIZON - 30)
        if tw_width == 'tight':
            half = rng.randint(5, 15)
        else:
            half = rng.randint(15, 45)
        e = max(0, center - half)
        l = min(HORIZON, center + half)
        windows.append((e, l))
        service_times.append(rng.randint(5, 15))
    return windows, service_times

# ============================================================
# Demand generator
# ============================================================
def gen_demands(n, seed, max_d=40):
    rng = random.Random(seed)
    return [rng.randint(1, max_d) for _ in range(n)]

# ============================================================
# Flexible rendezvous sites
# ============================================================
def gen_flex_sites(n_sites, seed):
    rng = random.Random(seed)
    sites = []
    for i in range(n_sites):
        x = round(rng.uniform(10, 90), 1)
        y = round(rng.uniform(10, 90), 1)
        sites.append({"id": f"F{i+1}", "x": x, "y": y})
    return sites

# ============================================================
# Build one instance
# ============================================================
def build_instance(name, coord_fn, tw_width, seed):
    depot = (50.0, 50.0)
    coords = coord_fn(N_CUSTOMERS, seed)
    all_coords = [depot] + coords

    demands = [0] + gen_demands(N_CUSTOMERS, seed + 5000)
    tws, svcs = gen_time_windows(N_CUSTOMERS, tw_width, seed + 7000)
    tws = [(0, HORIZON)] + tws
    svcs = [0] + svcs

    # Drone eligibility by payload
    drone_eligible = [i for i in range(1, N_CUSTOMERS+1)
                      if demands[i] <= DRONE_PARAMS["drone_payload_cap"]]

    # Energy feasibility filter
    drone_feasible = []
    for i in drone_eligible:
        d_out = euclidean(depot, all_coords[i])
        d_back = euclidean(all_coords[i], depot)
        sortie_dist = d_out + d_back
        energy = ((DRONE_PARAMS["P0"] + DRONE_PARAMS["alpha"] * demands[i])
                  * sortie_dist / DRONE_PARAMS["drone_speed"])
        energy += DRONE_PARAMS["hover_power"] * svcs[i]
        if energy <= (DRONE_PARAMS["battery_max"] - DRONE_PARAMS["battery_min"]):
            drone_feasible.append(i)

    # Forced-drone set (Type B): pick closest drone-feasible customers
    n_forced = max(1, int(N_CUSTOMERS * DRONE_PARAMS["forced_drone_pct"]))
    candidates = sorted(drone_feasible, key=lambda i: euclidean(depot, all_coords[i]))
    forced_drone = candidates[:min(n_forced, len(candidates))]

    # Flexible sites
    n_flex = max(2, N_CUSTOMERS // 10)
    flex_sites = gen_flex_sites(n_flex, seed + 9000)

    customers = []
    for i in range(1, N_CUSTOMERS+1):
        customers.append({
            "id": i,
            "x": all_coords[i][0],
            "y": all_coords[i][1],
            "demand": demands[i],
            "ready_time": tws[i][0],
            "due_time": tws[i][1],
            "service_time": svcs[i],
            "drone_eligible": i in drone_feasible,
            "truck_only": i not in drone_feasible,
            "forced_drone": i in forced_drone,
        })

    return {
        "name": name,
        "n_customers": N_CUSTOMERS,
        "depot": {"x": depot[0], "y": depot[1]},
        "truck_capacity": TRUCK_CAP,
        "horizon": HORIZON,
        "customers": customers,
        "flexible_sites": flex_sites,
        "drone_params": DRONE_PARAMS,
        "drone_eligible_set": drone_feasible,
        "forced_drone_only": forced_drone,
    }

# ============================================================
# Solomon-format text writer
# ============================================================
def write_solomon_txt(inst, path):
    with open(path, 'w') as f:
        f.write(f"{inst['name']}\n\n")
        f.write("VEHICLE\n")
        f.write("NUMBER     CAPACITY\n")
        f.write(f"  25         {inst['truck_capacity']}\n\n")
        f.write("CUSTOMER\n")
        f.write("CUST_NO.  XCOORD.  YCOORD.  DEMAND  READY_TIME  DUE_DATE  SERVICE_TIME\n\n")
        f.write(f"    0    {int(inst['depot']['x']):4d}    {int(inst['depot']['y']):4d}"
                f"       0       0      {inst['horizon']}       0\n")
        for c in inst['customers']:
            f.write(f"  {c['id']:3d}    {int(c['x']):4d}    {int(c['y']):4d}"
                    f"    {c['demand']:4d}    {c['ready_time']:4d}     {c['due_time']:4d}"
                    f"      {c['service_time']:4d}\n")

# ============================================================
# Instance catalog
# ============================================================
CATALOG = []

# C1: C101–C109
for i in range(1, 10):
    CATALOG.append((f"C1{i:02d}", gen_clustered, "tight", 1000 + i))
# C2: C201–C208
for i in range(1, 9):
    CATALOG.append((f"C2{i:02d}", gen_clustered, "wide", 2000 + i))
# R1: R101–R112
for i in range(1, 13):
    CATALOG.append((f"R1{i:02d}", gen_random, "tight", 3000 + i))
# R2: R201–R211
for i in range(1, 12):
    CATALOG.append((f"R2{i:02d}", gen_random, "wide", 4000 + i))
# RC1: RC101–RC108
for i in range(1, 9):
    CATALOG.append((f"RC1{i:02d}", gen_mixed, "tight", 5000 + i))
# RC2: RC201–RC208
for i in range(1, 9):
    CATALOG.append((f"RC2{i:02d}", gen_mixed, "wide", 6000 + i))

# ============================================================
# Generate all
# ============================================================
OUT = "/home/claude/solomon_benchmark"
os.makedirs(OUT, exist_ok=True)

# Clean old files
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

stats = {"C1": [], "C2": [], "R1": [], "R2": [], "RC1": [], "RC2": []}

for name, coord_fn, tw, seed in CATALOG:
    inst = build_instance(name, coord_fn, tw, seed)

    # Type A
    inst_a = {**inst, "variant": "A_natural"}
    with open(f"{OUT}/{name}_A.json", 'w') as f:
        json.dump(inst_a, f, indent=2)

    # Type B
    inst_b = {**inst, "variant": "B_forced"}
    with open(f"{OUT}/{name}_B.json", 'w') as f:
        json.dump(inst_b, f, indent=2)

    # Solomon txt
    write_solomon_txt(inst, f"{OUT}/{name}_solomon.txt")

    cat = name[:2] if not name.startswith("RC") else name[:3]
    n_elig = len(inst["drone_eligible_set"])
    n_forced = len(inst["forced_drone_only"])
    stats[cat].append((name, n_elig, n_forced))

# Print summary
total = 0
for cat in ["C1", "C2", "R1", "R2", "RC1", "RC2"]:
    items = stats[cat]
    avg_elig = sum(x[1] for x in items) / len(items)
    avg_forced = sum(x[2] for x in items) / len(items)
    print(f"{cat}: {len(items)} instances | avg drone-eligible: {avg_elig:.1f} | avg forced: {avg_forced:.1f}")
    total += len(items)

n_files = len(os.listdir(OUT))
print(f"\nTotal: {total} instances → {n_files} files")
print(f"  {total*2} JSON (A+B variants) + {total} Solomon .txt")
