# Input Format

Each instance is a JSON file. Below is the schema with field descriptions.

## JSON Schema

```json
{
  "name": "C101",                    // Instance name (Solomon-style)
  "n_customers": 100,               // Number of customers
  "variant": "A_natural" | "B_forced",  // Variant type
  "depot": {
    "x": 50.0,                       // Depot x-coordinate
    "y": 50.0                        // Depot y-coordinate
  },
  "truck_capacity": 200,            // Q^T: max truck load
  "horizon": 230,                   // Planning horizon (depot due date)

  "customers": [                     // Array of n_customers objects
    {
      "id": 1,                       // Customer ID (1-indexed)
      "x": 12.6,                     // x-coordinate
      "y": 45.7,                     // y-coordinate
      "demand": 22,                  // d_i: demand weight
      "ready_time": 145,            // e_i: earliest service time
      "due_time": 173,              // l_i: latest desired service time
      "service_time": 9,            // s_i (used for both s_i^T and s_i^D)
      "drone_eligible": false,      // true if customer is in C^D
      "truck_only": true,           // true if customer MUST be served by truck
      "forced_drone": false         // true if truck edges removed (variant B only)
    }
    // ... (100 customers)
  ],

  "flexible_sites": [               // Flexible launch/recovery sites F
    {
      "id": "F1",                    // Site ID
      "x": 35.2,                     // x-coordinate
      "y": 67.8                      // y-coordinate
    }
    // ... (~10 sites)
  ],

  "drone_params": {                  // Drone and charging parameters
    "drone_speed": 40.0,            // v_drone (distance units / time unit)
    "truck_speed": 30.0,            // v_truck
    "battery_max": 1.0,             // B_max (normalized)
    "battery_min": 0.1,             // B_min (safe reserve)
    "charge_rate_stopped": 0.05,    // rho_s (battery / time unit)
    "charge_rate_moving": 0.02,     // rho_m (battery / time unit)
    "launch_time": 1.0,             // ell (time units)
    "recovery_time": 1.0,           // r (time units)
    "drone_payload_cap": 10,        // Q^D
    "P0": 0.005,                    // Base drone power (no load)
    "alpha": 0.001,                 // Power increase per unit payload
    "hover_power": 0.008,           // P_hover
    "detour_factor": 1.3,           // Truck distance = detour_factor * Euclidean
    "forced_drone_pct": 0.15        // Fraction of customers forced to drone (variant B)
  },

  "drone_eligible_set": [4, 7, ...],   // List of drone-eligible customer IDs
  "forced_drone_only": [4, 7, ...]     // List of drone-only customer IDs (variant B)
}
```

## Distance and time computation

```python
import math

def euclidean(a, b):
    return math.sqrt((a["x"] - b["x"])**2 + (a["y"] - b["y"])**2)

# Truck travel time between nodes i and g:
def truck_time(node_i, node_g, params):
    dist = params["detour_factor"] * euclidean(node_i, node_g)
    return dist / params["truck_speed"]

# Drone flight time between nodes i and j:
def drone_time(node_i, node_j, params):
    dist = euclidean(node_i, node_j)
    return dist / params["drone_speed"]

# Drone sortie energy (launch at i, serve j, recover at g):
def drone_energy(node_i, node_j, node_g, demand_j, hover_time, params):
    dist_ij = euclidean(node_i, node_j)
    dist_jg = euclidean(node_j, node_g)
    t_ij = dist_ij / params["drone_speed"]
    t_jg = dist_jg / params["drone_speed"]
    energy = (params["P0"] + params["alpha"] * demand_j) * t_ij  # loaded
    energy += params["P0"] * t_jg                                 # unloaded
    energy += params["hover_power"] * hover_time                  # hover
    return energy

# Truck energy (simplified: proportional to distance):
def truck_energy(node_i, node_g, params):
    return params["detour_factor"] * euclidean(node_i, node_g)
```

## Additional parameters (not in instance file)

These are experiment-level parameters that the algorithm runner sets:

| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| Number of pairs | M | 5 | Number of truck-drone pairs |
| Tardiness limit | eps_L | 50.0 | Max total weighted tardiness |
| Tardiness weights | w_i | 1.0 | Weight per customer (uniform) |
| Charging efficiency | eta_c | 1.0 | Charging efficiency factor |
| Initial battery | B_k^0 | 1.0 | = B_max |

## Variant B: forced drone customers

In variant B instances, customers with `forced_drone: true` have **no truck edges**. The truck cannot visit these customers. They must be:
1. Assigned to a drone sortie, AND
2. The drone must be launched from and recovered at truck-accessible nodes.

If your algorithm represents truck routes as permutations, forced-drone customers must NOT appear in truck routes. They appear only as drone assignments j_{k,h}.
