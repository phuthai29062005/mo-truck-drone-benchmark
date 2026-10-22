# Output Format

Each algorithm must produce a JSON file containing its Pareto front approximation.

## Solution file schema

```json
{
  "instance": "R101_A",                // Instance name + variant
  "algorithm": "NSGA-II",             // Algorithm name
  "n_pairs": 5,                       // Number of truck-drone pairs used
  "eps_L": 50.0,                      // Tardiness limit used
  "runtime_seconds": 123.4,           // Wall-clock runtime
  "n_evaluations": 500000,            // Total solution evaluations
  "seed": 42,                         // Random seed
  "run_id": 1,                        // Run number (for multi-run experiments)

  "pareto_front": [                   // List of non-dominated solutions
    {
      "id": 1,
      "makespan": 185.3,              // f_1: T_max
      "energy": 1234.5,               // f_2: E_system
      "tardiness": 12.0,              // L_total (must be <= eps_L)
      "n_drone_sorties": 15,          // Number of drone sorties used
      "routes": [                      // Optional: full route detail
        {
          "pair_id": 1,               // Truck-drone pair k
          "truck_route": [0, 3, 12, 45, 0],  // Truck stop sequence (node IDs)
          "segments": [
            {
              "type": "truck",        // Pure-truck segment
              "from": 0,
              "to": 3,
              "depart_time": 0.0,
              "arrive_time": 5.2,
              "charge_time": 0.0,     // c_{k,h}: extra stop time for charging
              "charge_amount": 0.0    // q_{k,h}: battery charged
            },
            {
              "type": "drone",        // Cooperative segment (drone sortie)
              "from": 3,              // Launch node
              "to": 12,              // Recovery node
              "drone_customer": 7,    // Customer served by drone
              "depart_time": 14.2,
              "arrive_time": 22.8,
              "drone_energy": 0.15,   // E^D for this sortie
              "hover_time": 1.3,      // H^D: drone hover wait
              "truck_wait": 0.0,      // W^T: truck wait for drone
              "charge_time": 2.0,
              "charge_amount": 0.1,
              "battery_before": 0.85, // B_{k,h} before charge
              "battery_after": 0.80   // B_{k,h+1} after sortie
            }
            // ... more segments
          ]
        }
        // ... more pairs
      ]
    }
    // ... more non-dominated solutions
  ]
}
```

## Minimal output (required fields only)

At minimum, provide the Pareto front points with objectives and feasibility:

```json
{
  "instance": "R101_A",
  "algorithm": "NSGA-II",
  "runtime_seconds": 123.4,
  "seed": 42,
  "run_id": 1,
  "pareto_front": [
    {"makespan": 185.3, "energy": 1234.5, "tardiness": 12.0},
    {"makespan": 192.1, "energy": 1100.2, "tardiness": 8.5},
    {"makespan": 210.0, "energy": 980.0,  "tardiness": 0.0}
  ]
}
```

## Notes

1. **All solutions in `pareto_front` must be feasible**: `tardiness <= eps_L`, battery constraints satisfied, all customers served exactly once, etc.
2. **Non-dominated**: the front should contain only mutually non-dominated solutions (in the (makespan, energy) space).
3. **Multiple runs**: run each algorithm 30 times with different seeds. Each run produces one file. Name files as: `{algorithm}_{instance}_{run_id}.json`.
4. **Route detail is optional** but recommended for validation. The validator script can check feasibility when routes are provided.
5. Flexible sites in `truck_route` use their string ID (e.g., "F3").

## File naming convention

```
results/
  {algorithm}/
    {algorithm}_{instance}_{run_id}.json
```

Example:
```
results/
  NSGA-II/
    NSGA-II_R101_A_01.json
    NSGA-II_R101_A_02.json
    ...
    NSGA-II_R101_A_30.json
    NSGA-II_R101_B_01.json
    ...
```
