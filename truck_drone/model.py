"""Route simulation implementing sections 6–9 of the problem specification.

Stationary charging uses only *additional* stop time. No charging is credited
during customer service, waiting, or a sortie. Demand includes drone parcels.
The horizon is descriptive: the specification defines no hard depot deadline.
"""

import math
from dataclasses import dataclass

TOL = 1e-7


@dataclass
class Evaluation:
    solution: dict
    violation: float
    errors: list

    @property
    def objectives(self):
        return self.solution["makespan"], self.solution["energy"]


class Problem:
    def __init__(self, instance, n_pairs=5, eps_L=50.0, truck_capacity=None,
                 eta_c=1.0):
        if n_pairs < 1 or eps_L < 0 or not math.isfinite(eps_L):
            raise ValueError("n_pairs must be positive and eps_L finite and nonnegative")
        if not 0 < eta_c <= 1:
            raise ValueError("eta_c must be in (0, 1]")
        self.instance = instance
        self.n_pairs, self.eps_L, self.eta_c = n_pairs, eps_L, eta_c
        self.capacity = truck_capacity if truck_capacity is not None else instance["truck_capacity"]
        if self.capacity <= 0 or not math.isfinite(self.capacity):
            raise ValueError("truck capacity must be finite and positive")
        self.p = instance["drone_params"]
        self.customers = {c["id"]: c for c in instance["customers"]}
        self.ids = tuple(self.customers)
        self.flex = {f["id"]: f for f in instance.get("flexible_sites", [])}
        self.nodes = {0: instance["depot"], **self.customers, **self.flex}
        # The shipped generator leaves B's flags and set in A as well.
        # The explicit variant determines whether truck edges are removed.
        self.forced = (set(instance.get("forced_drone_only", [])) |
                       {i for i, c in self.customers.items() if c.get("forced_drone")}) if instance.get("variant", "").startswith("B") else set()
        self.eligible = {i for i, c in self.customers.items()
                         if c.get("drone_eligible", False) and not c.get("truck_only", False)
                         and c["demand"] <= self.p["drone_payload_cap"]}
        self.dist = {(i, j): math.hypot(a["x"] - b["x"], a["y"] - b["y"])
                     for i, a in self.nodes.items() for j, b in self.nodes.items()}

    def preflight(self):
        errors = []
        demand = sum(c["demand"] for c in self.customers.values())
        if demand > self.n_pairs * self.capacity + TOL:
            errors.append(f"Total demand {demand} > fleet capacity {self.n_pairs * self.capacity:g}; "
                          f"at least {math.ceil(demand / self.capacity)} pairs required (necessary bound only)")
        if any(c["demand"] > self.capacity for c in self.customers.values()):
            errors.append("A customer demand exceeds truck capacity")
        if self.forced - self.eligible:
            errors.append(f"Forced drone customers ineligible: {sorted(self.forced - self.eligible)}")
        return errors

    def flight(self, source, customer, target, depart):
        p, c = self.p, self.customers[customer]
        out = self.dist[source, customer] / p["drone_speed"]
        back = self.dist[customer, target] / p["drone_speed"]
        truck = self.dist[source, target] * p["detour_factor"] / p["truck_speed"]
        start = max(depart + p["launch_time"] + out, c["ready_time"])
        complete = start + c["service_time"]
        duration = complete + back - depart
        hover = max(0.0, truck - duration)
        energy = ((p["P0"] + p["alpha"] * c["demand"]) * out +
                  p["P0"] * back + p["hover_power"] * hover)
        return energy, hover, max(0.0, duration - truck), complete, max(truck, duration) + p["recovery_time"]

    def simulate(self, routes, *, schedule=False):
        """Recompute a plan. schedule=True constructs minimal/proactive charges.

        Otherwise, prescribed c and q are checked, never silently clamped.
        Recorded objective/timing fields are not trusted by this simulator.
        """
        p = self.p
        errors, served, output = [], [], []
        capacity_excess = battery_excess = 0.0
        tardiness = truck_energy = drone_energy = makespan = 0.0
        sorties = 0
        if len(routes) > self.n_pairs:
            errors.append("Too many routes/pairs")
        pair_ids = [r["pair_id"] for r in routes]
        if len(set(pair_ids)) != len(pair_ids) or any(k not in range(1, self.n_pairs + 1) for k in pair_ids):
            errors.append("Invalid or duplicate pair_id")
        for route in routes:
            nodes, segments = route["truck_route"], route["segments"]
            if len(nodes) < 2 or nodes[0] != 0 or nodes[-1] != 0:
                raise ValueError("Truck route must start and finish at depot")
            if any(n not in self.nodes for n in nodes):
                raise ValueError("Unknown truck node")
            if len(segments) != len(nodes) - 1:
                raise ValueError("One segment required per consecutive pair of stops")
            load, clock, battery = 0.0, 0.0, p["battery_max"]
            rendered = []
            for h, raw in enumerate(segments):
                i, g = nodes[h:h+2]
                if raw["from"] != i or raw["to"] != g:
                    raise ValueError("Segment endpoints do not match truck_route")
                if raw["type"] not in ("truck", "drone"):
                    raise ValueError("Unknown segment type")
                if i in self.customers:
                    c = self.customers[i]
                    served.append(i)
                    load += c["demand"]
                    if i in self.forced:
                        errors.append(f"Forced drone customer {i} visited by truck")
                    clock = max(clock, c["ready_time"]) + c["service_time"]
                    tardiness += c.get("weight", 1.0) * max(0.0, clock - c["due_time"])
                base_depart = clock
                truck_duration = self.dist[i, g] * p["detour_factor"] / p["truck_speed"]
                e = hover = wait = 0.0
                if raw["type"] == "drone":
                    j = raw["drone_customer"]
                    if j not in self.customers:
                        raise ValueError("Unknown drone customer")
                    served.append(j)
                    load += self.customers[j]["demand"]
                    if j not in self.eligible:
                        errors.append(f"Customer {j} not eligible for drone")
                    if schedule:
                        fraction = raw.get("charge_fraction", 0.0)
                        # Energy may grow with departure time as hover increases.
                        # Bisection solves charging and hover together.
                        def deficit(c_time):
                            energy = self.flight(i, j, g, base_depart + c_time)[0]
                            target = min(p["battery_max"], p["battery_min"] + energy +
                                         fraction * max(0.0, p["battery_max"] - p["battery_min"] - energy))
                            q = min(p["battery_max"] - battery, self.eta_c * p["charge_rate_stopped"] * c_time)
                            return target - battery - q
                        rate = self.eta_c * p["charge_rate_stopped"]
                        lo, hi = 0.0, (p["battery_max"] - battery) / rate if rate > 0 else 0.0
                        if deficit(0) > 0 and hi > 0:
                            for _ in range(45):
                                mid = (lo + hi) / 2
                                if deficit(mid) > 0:
                                    lo = mid
                                else:
                                    hi = mid
                            charge_time = hi
                        else:
                            charge_time = 0.0
                        charge = min(p["battery_max"] - battery, rate * charge_time)
                    else:
                        charge_time, charge = raw.get("charge_time", 0.0), raw.get("charge_amount", 0.0)
                    clock += charge_time
                    e, hover, wait, complete, duration = self.flight(i, j, g, clock)
                    tardiness += self.customers[j].get("weight", 1.0) * max(0.0, complete - self.customers[j]["due_time"])
                    drone_energy += e
                    sorties += 1
                else:
                    charge_time = 0.0 if schedule else raw.get("charge_time", 0.0)
                    moving = self.eta_c * p["charge_rate_moving"] * truck_duration
                    charge = min(p["battery_max"] - battery, moving) if schedule else raw.get("charge_amount", 0.0)
                    clock += charge_time
                    duration = truck_duration
                if not all(math.isfinite(v) for v in (charge_time, charge)):
                    raise ValueError("Nonfinite charge")
                limit = self.eta_c * (p["charge_rate_stopped"] * charge_time +
                                     (p["charge_rate_moving"] * truck_duration if raw["type"] == "truck" else 0))
                if charge_time < -TOL or charge < -TOL or charge > limit + TOL:
                    errors.append("Invalid charging time/amount or charging rate exceeded")
                before = battery
                battery_excess += max(0.0, battery + charge - p["battery_max"])
                battery += charge - e
                battery_excess += max(0.0, p["battery_min"] - battery)
                clock += duration
                truck_energy += self.dist[i, g] * p["detour_factor"]
                seg = {"type": raw["type"], "from": i, "to": g,
                       "depart_time": base_depart + charge_time, "arrive_time": clock,
                       "charge_time": charge_time, "charge_amount": charge,
                       "battery_before": before, "battery_after": battery}
                if raw["type"] == "drone":
                    seg.update(drone_customer=j, drone_energy=e, hover_time=hover, truck_wait=wait)
                rendered.append(seg)
            capacity_excess += max(0.0, load - self.capacity)
            makespan = max(makespan, clock)
            output.append(dict(pair_id=route["pair_id"], truck_route=list(nodes), segments=rendered))
        if sorted(served) != sorted(self.ids):
            errors.append("Customers must be served exactly once")
        late = max(0.0, tardiness - self.eps_L)
        if capacity_excess > TOL:
            errors.append(f"Truck capacity exceeded by {capacity_excess:g}")
        if battery_excess > TOL:
            errors.append(f"Battery violation {battery_excess:g}")
        if late > TOL:
            errors.append(f"Tardiness {tardiness:g} exceeds eps_L {self.eps_L:g}")
        structural = sum(not s.startswith(("Truck capacity", "Battery violation", "Tardiness")) for s in errors)
        violation = (capacity_excess / self.capacity + battery_excess / p["battery_max"] +
                     late / max(1.0, self.eps_L) + structural)
        if not errors:
            violation = 0.0
        return Evaluation(dict(makespan=makespan, energy=truck_energy + drone_energy / self.eta_c,
                               tardiness=tardiness, n_drone_sorties=sorties, routes=output), violation, errors)
