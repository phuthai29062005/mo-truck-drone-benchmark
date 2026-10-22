# Problem Specification

## Multi-objective Truck-Drone Routing with Flexible Rendezvous, Partial Charging, and Soft Time Windows

### 1. Problem type

Static, offline, deterministic. All data is known before planning.

### 2. System configuration

1. **M** truck-drone pairs. Each truck carries exactly one drone.
2. Trucks depart from and return to the depot (node 0).
3. Each customer is served exactly once, by either the truck or the drone.
4. Each drone sortie serves exactly **one** customer.
5. The drone launches at truck stop h and recovers at stop h+1.
6. Launch/recovery nodes can be: depot, customer node, or a flexible site.
7. The drone must return to the **same** truck that launched it.
8. Sorties of the same pair do not overlap.
9. Truck and drone synchronize at the recovery node before continuing.
10. The drone charges (partially) while on the truck: while moving or while stopped.
11. The drone does NOT charge during a sortie.
12. Customers have soft time windows [e_i, l_i]. Early arrival waits; late arrival incurs tardiness.

### 3. Sets

- **C** = {1, ..., n}: customers
- **F** = {n+1, ..., n+f}: flexible launch/recovery sites
- **V** = {0} U C U F: all nodes; 0 = depot
- **K** = {1, ..., M}: truck-drone pairs
- **C^D** = {i in C : d_i <= Q^D and i is drone-eligible}: drone-eligible customers

### 4. Parameters

#### 4.1 Customer parameters
For each customer i in C:
- **d_i**: demand (weight/volume)
- **s_i^T**: truck service time at customer i
- **s_i^D**: drone service time at customer i
- **e_i**: earliest service time (ready time)
- **l_i**: latest desired service time (due date)
- **w_i** >= 0: tardiness weight

For depot and flexible sites: s_i^T = s_i^D = 0.

#### 4.2 Vehicle parameters
- **Q^T**: truck capacity
- **Q^D**: drone payload capacity (= drone_payload_cap)
- **B_max**: maximum battery capacity (normalized to 1.0)
- **B_min**: minimum safe battery level (= 0.1)
- **B_k^0**: initial battery of drone k (= B_max)
- **rho_s**: charge rate while truck is stopped (= 0.05 per time unit)
- **rho_m**: charge rate while truck is moving, drone on board (= 0.02 per time unit)
- **eta_c**: charging efficiency (= 1.0 in benchmarks)
- **l** (ell): launch preparation time (= 1.0)
- **r**: recovery time (= 1.0)

#### 4.3 Travel time and energy
- **v_truck** = 30: truck speed
- **v_drone** = 40: drone speed
- **tau^T_{ig}** = dist_truck(i,g) / v_truck: truck travel time
  - In variant A: dist_truck(i,g) = detour_factor * euclidean(i,g) = 1.3 * euclidean(i,g)
  - In variant B: dist_truck(i,g) = 1.3 * euclidean(i,g), but some edges are removed (forced_drone customers)
- **tau^D_{ij}** = euclidean(i,j) / v_drone: drone flight time
- **E^T_{ig}**: truck energy = proportional to dist_truck(i,g) (simplified: E^T = dist_truck)
- **P_0** = 0.005: base drone power (no load)
- **alpha** = 0.001: power increase per unit payload
- **P_hover** = 0.008: hover power
- **E_{L/R}**: launch/recovery energy (simplified: 0 in benchmarks, included in sortie time)

#### 4.4 Drone energy model

For a cooperative segment (launch at i, serve customer j, recover at g):

```
E^D_{ijg} = (P_0 + alpha * d_j) * tau^D_{ij}    # loaded flight i -> j
           + P_0 * tau^D_{jg}                      # unloaded flight j -> g
           + P_hover * H^D                          # hover wait
           + E_{L/R}                                # launch/recovery energy
```

#### 4.5 Service quality
- **eps_L**: maximum total weighted tardiness allowed

### 5. Solution representation

A solution X consists of, for each pair k:
- Truck route: R_k = (v_{k,0}, v_{k,1}, ..., v_{k,H_k}), with v_{k,0} = v_{k,H_k} = 0
- Segment types: u_{k,h} in {0, 1}. 0 = pure-truck, 1 = cooperative (drone sortie)
- Drone assignments: j_{k,h} for cooperative segments
- Charging plan: q_{k,h} (charge amount), c_{k,h} (stop time for charging)

### 6. Timing

#### 6.1 Truck at a stop
```
D_{k,h} = max(A_{k,h}, e_{v_{k,h}}) + sigma_{k,h} + c_{k,h}
```
where sigma_{k,h} = s^T_{v_{k,h}} if truck serves customer there, 0 otherwise.

#### 6.2 Pure-truck segment (u_{k,h} = 0)
```
A_{k,h+1} = D_{k,h} + tau^T_{v_{k,h}, v_{k,h+1}}
```

#### 6.3 Cooperative segment (u_{k,h} = 1)
Launch node i = v_{k,h}, drone customer j = j_{k,h}, recovery node g = v_{k,h+1}.

```
A_j^D = D_{k,h} + ell + tau^D_{ij}          # drone arrives at customer
S_j^D = max(A_j^D, e_j)                      # drone starts service
C_j   = S_j^D + s_j^D                        # service completion

Delta^D = ell + tau^D_{ij} + max(0, e_j - A_j^D) + s_j^D + tau^D_{jg}
Delta^T = tau^T_{ig}

W^T  = max(0, Delta^D - Delta^T)             # truck waits for drone
H^D  = max(0, Delta^T - Delta^D)             # drone hovers waiting for truck

A_{k,h+1} = D_{k,h} + max(Delta^T, Delta^D) + r
```

### 7. Battery dynamics

```
B_{k,0}   = B_k^0                            # initial battery

# Charge amount bounded by:
0 <= q_{k,h} <= eta_c * [rho_s * c_{k,h} + (1 - u_{k,h}) * rho_m * tau^T]

# Cannot exceed max:
B_{k,h} + q_{k,h} <= B_max

# Must have enough before launch:
B_{k,h} + q_{k,h} >= E^D + B_min   (if u_{k,h} = 1)

# Update:
B_{k,h+1} = B_{k,h} + q_{k,h} - u_{k,h} * E^D

# Bounds:
B_min <= B_{k,h} <= B_max   for all k, h
```

### 8. Soft time windows

```
L_i = max(0, C_i - l_i)                      # tardiness
L_total = sum_{i in C} w_i * L_i             # total weighted tardiness
L_total <= eps_L                              # constraint
```

### 9. Objectives

```
f_1(X) = T_max = max_{k in K} A_{k, H_k}    # minimize makespan
f_2(X) = E_truck + E_drone / eta_c           # minimize total system energy

min (f_1, f_2)   subject to all constraints above
```

Output: a Pareto front approximation (set of non-dominated solutions).

### 10. Variant B specifics

In variant B, customers marked `forced_drone: true` have no truck edges. They MUST be served by drone. The truck cannot visit them. Algorithms must ensure these customers are assigned to drone sorties.
