import copy
import json
import random
import unittest
from pathlib import Path

from scripts.validate_solution import validate_front, validate_solution
from truck_drone.algorithms import Individual, dominates, normalize, optimize, survival
from truck_drone.encoding import Encoding
from truck_drone.model import Evaluation, Problem


def instance(variant="A_natural"):
    params = dict(drone_speed=1.0, truck_speed=1.0, battery_max=1.0,
                  battery_min=.1, charge_rate_stopped=.05, charge_rate_moving=.02,
                  launch_time=1.0, recovery_time=1.0, drone_payload_cap=10,
                  P0=.005, alpha=.001, hover_power=.008, detour_factor=1.0)
    customers = [dict(id=i, x=float(i), y=0.0, demand=2, ready_time=0,
                      due_time=1000, service_time=1, drone_eligible=True,
                      truck_only=False, forced_drone=(i == 1)) for i in range(1, 9)]
    return dict(name="tiny", variant=variant, n_customers=len(customers),
                depot=dict(x=0.0, y=0.0), customers=customers, truck_capacity=20,
                horizon=2000, drone_params=params, forced_drone_only=[1],
                flexible_sites=[dict(id="F1", x=3.5, y=1.0)])


def route(nodes, drone=None):
    segs = []
    for h, (a, b) in enumerate(zip(nodes, nodes[1:])):
        seg = {"type": "truck", "from": a, "to": b}
        if drone and h in drone:
            seg.update(type="drone", drone_customer=drone[h])
        segs.append(seg)
    return dict(pair_id=1, truck_route=nodes, segments=segs)


class SimulationTests(unittest.TestCase):
    def single(self):
        data = instance()
        data["customers"] = data["customers"][:1]
        data["n_customers"] = 1
        return data

    def test_hand_computed_truck_and_completion_tardiness(self):
        data = self.single()
        c = data["customers"][0]
        c.update(ready_time=5, due_time=5, service_time=2, weight=3)
        ev = Problem(data, 1).simulate([route([0, 1, 0])], schedule=True)
        self.assertEqual(ev.errors, [])
        self.assertEqual(ev.objectives, (8.0, 2.0))
        self.assertEqual(ev.solution["tardiness"], 6)

    def test_hand_computed_flight_and_hover(self):
        data = self.single()
        data["flexible_sites"] = [dict(id="F1", x=10., y=0.)]
        data["drone_params"]["truck_speed"] = .5
        ev = Problem(data, 1).simulate([route([0, "F1", 0], {0: 1})], schedule=True)
        # Flight: launch 1 + outbound 1 + service 1 + return 9 = 12.
        # Truck duration 20, hover 8, energy .007+.045+.064=.116.
        seg = ev.solution["routes"][0]["segments"][0]
        self.assertAlmostEqual(seg["hover_time"], 8)
        self.assertAlmostEqual(seg["drone_energy"], .116)
        self.assertEqual(seg["charge_amount"], 0)
        self.assertEqual(ev.solution["makespan"], 41)
        self.assertAlmostEqual(ev.solution["energy"], 20.116)

    def test_drone_early_wait_and_truck_wait(self):
        data = self.single()
        data["customers"][0].update(ready_time=10, due_time=10)
        ev = Problem(data, 1).simulate([route([0, 0], {0: 1})], schedule=True)
        seg = ev.solution["routes"][0]["segments"][0]
        self.assertEqual(ev.solution["makespan"], 13)
        self.assertEqual(ev.solution["tardiness"], 1)
        self.assertEqual(seg["truck_wait"], 12)
        self.assertEqual(seg["hover_time"], 0)
        self.assertAlmostEqual(seg["drone_energy"], .012)

    def test_partial_charging_and_efficiency(self):
        data = instance("B_forced")
        data["customers"] = data["customers"][:2]
        for c in data["customers"]:
            c["x"] = 20.0
        data["drone_params"].update(P0=.01, alpha=.005)
        p = Problem(data, 1, eta_c=.5)
        ev = p.simulate([route([0, 0, 0], {0: 1, 1: 2})], schedule=True)
        segs = ev.solution["routes"][0]["segments"]
        self.assertEqual(ev.errors, [])
        self.assertAlmostEqual(segs[0]["drone_energy"], .6)
        self.assertAlmostEqual(segs[1]["charge_amount"], .3)
        self.assertAlmostEqual(segs[1]["charge_time"], 12)
        self.assertAlmostEqual(segs[1]["battery_after"], .1)
        self.assertAlmostEqual(ev.solution["energy"], 2.4)
        self.assertEqual(p.simulate(ev.solution["routes"]).errors, [])

    def test_stationary_charge_accounts_for_changed_hover(self):
        data = instance()
        data["customers"] = data["customers"][:2]
        data["customers"][0]["x"] = 20.
        data["customers"][1].update(x=1., ready_time=80)
        data["drone_params"].update(P0=.01, alpha=.005, truck_speed=.1)
        # First flight depletes battery. Second flight synchronizes at F1;
        # charging can reduce early waiting and introduce hover.
        plan = route([0, 0, "F1", 0], {0: 1, 1: 2})
        plan["segments"][1]["charge_fraction"] = .75
        p = Problem(data, 1)
        ev = p.simulate([plan], schedule=True)
        self.assertEqual(ev.errors, [])
        second = ev.solution["routes"][0]["segments"][1]
        self.assertGreater(second["charge_time"], 0)
        self.assertGreater(second["hover_time"], 0)
        self.assertEqual(p.simulate(ev.solution["routes"]).errors, [])

    def test_capacity_includes_drone_parcel(self):
        data = self.single()
        p = Problem(data, 1, truck_capacity=1)
        ev = p.simulate([route([0, 0], {0: 1})], schedule=True)
        self.assertGreater(ev.violation, 0)
        self.assertTrue(any("capacity" in e for e in ev.errors))

    def test_variant_a_ignores_stale_b_flags(self):
        data = self.single()
        self.assertEqual(Problem(data, 1).simulate([route([0, 1, 0])]).errors, [])
        data["variant"] = "B_forced"
        self.assertTrue(any("Forced" in e for e in Problem(data, 1).simulate([route([0, 1, 0])]).errors))

    def test_validator_rejects_tampered_physics(self):
        data = self.single()
        sol = Problem(data, 1).simulate([route([0, 0], {0: 1})], schedule=True).solution
        self.assertEqual(validate_solution(data, sol, M=1)[0], [])
        for field in ("makespan", "energy", "tardiness"):
            bad = copy.deepcopy(sol)
            bad[field] += 1
            self.assertTrue(validate_solution(data, bad, M=1)[0])
        for field in ("arrive_time", "drone_energy", "battery_after"):
            bad = copy.deepcopy(sol)
            bad["routes"][0]["segments"][0][field] += 1
            self.assertTrue(validate_solution(data, bad, M=1)[0])
        for field, value in (("charge_amount", .1), ("charge_time", -1)):
            bad = copy.deepcopy(sol)
            bad["routes"][0]["segments"][0][field] = value
            self.assertTrue(validate_solution(data, bad, M=1)[0])
        bad = copy.deepcopy(sol)
        bad["routes"][0]["segments"][0]["to"] = "F1"
        self.assertTrue(validate_solution(data, bad, M=1)[0])
        self.assertTrue(validate_solution(data, {k:v for k,v in sol.items() if k != "routes"})[0])


class AlgorithmTests(unittest.TestCase):
    def test_all_algorithms_budget_repeatability_and_feasibility(self):
        for variant in ("A_natural", "B_forced"):
            p = Problem(instance(variant), n_pairs=2)
            for algorithm in ("NSGA-II", "NSGA-III", "MOEA/D"):
                with self.subTest(variant=variant, algorithm=algorithm):
                    a = optimize(p, algorithm, 12, 61, 30, seed=7)
                    b = optimize(p, algorithm, 12, 61, 30, seed=7)
                    self.assertEqual(a["n_evaluations"], 61)
                    self.assertEqual(a["status"], "ok")
                    self.assertEqual(a["pareto_front"], b["pareto_front"])
                    a.update(n_pairs=2)
                    self.assertEqual(validate_front(p.instance, a)[0], [])

    def test_encoding_variation_preserves_permutation_and_forced_mode(self):
        p, rng = Problem(instance("B_forced"), 2), random.Random(2)
        enc = Encoding(p)
        a, b = enc.initial(rng, 0), enc.initial(rng, 1)
        for _ in range(100):
            a = enc.offspring(a, b, rng)
            self.assertEqual(sorted(a.order), sorted(p.ids))
            self.assertTrue(a.modes[enc.index[1]])
            self.assertEqual(sorted(i for r in enc.decode(a).solution["routes"] for i in r["truck_route"] if isinstance(i, int) and i > 0).count(1), 0)

    def test_preflight_all_112_instances(self):
        paths = list((Path(__file__).resolve().parents[1] / "instances").glob("*.json"))
        self.assertEqual(len(paths), 112)
        for path in paths:
            p = Problem(json.loads(path.read_text()))
            result = optimize(p, max_evaluations=100)
            self.assertEqual(result["status"], "infeasible_precheck")
            self.assertEqual(result["n_evaluations"], 0)
            self.assertEqual(result["pareto_front"], [])

    def test_constraint_selection_and_degenerate_normalization(self):
        def ind(f, cv=0):
            return Individual(None, Evaluation(dict(makespan=f[0], energy=f[1]), cv, []))
        feasible, infeasible = ind((10, 10)), ind((1, 1), .1)
        self.assertTrue(dominates(feasible, infeasible))
        points = [ind((0, 5)), ind((1, 4)), ind((2, 3)), ind((3, 2)), ind((4, 1)), ind((5, 0)), ind((6, 6))]
        for algo in ("NSGA-II", "NSGA-III"):
            selected = survival(points, 4, algo, random.Random(4))
            self.assertEqual(len(selected), 4)
            self.assertNotIn(points[-1], selected)
        self.assertEqual(normalize([(2, 2), (2, 2)]), [(0, 0), (0, 0)])
        self.assertEqual(normalize([(1, 3), (3, 1)]), [(0, 1), (1, 0)])

    def test_timeout(self):
        result = optimize(Problem(instance(), 2), population_size=100,
                          max_evaluations=100, time_limit=1e-9)
        self.assertEqual(result["n_evaluations"], 0)
        self.assertEqual(result["status"], "no_feasible_solution")


if __name__ == "__main__":
    unittest.main()
