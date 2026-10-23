"""Shared permutation, service-mode, pair, rendezvous and charge genes.

All three baselines use identical initialization, repair, crossover and mutation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Genome:
    order: tuple
    modes: tuple
    pairs: tuple
    sites: tuple
    charges: tuple


class Encoding:
    def __init__(self, problem):
        self.problem = problem
        self.index = {c: i for i, c in enumerate(problem.ids)}
        self.site_ids = (None, *problem.flex)

    def initial(self, rng, index):
        p = self.problem
        order = list(p.ids)
        # Ready-time seeds establish viable service sequences; random seeds
        # preserve exploration. Jitter changes assignments without erasing TWs.
        if index % 5 != 4:
            jitter = (index % 5) * 4
            keys = {i: p.customers[i]["ready_time"] + rng.uniform(-jitter, jitter) for i in order}
            order.sort(key=keys.get)
        else:
            rng.shuffle(order)
        modes = tuple(i in p.forced or (i in p.eligible and rng.random() < (index % 4) / 3)
                      for i in p.ids)
        loads, clocks, tails = [0.0]*p.n_pairs, [0.0]*p.n_pairs, [0]*p.n_pairs
        pairs = [0]*len(order)
        for i in order:
            c = p.customers[i]
            available = [k for k in range(p.n_pairs) if loads[k] + c["demand"] <= p.capacity]
            choices = available or list(range(p.n_pairs))
            def score(k):
                arrival = clocks[k] + p.dist[tails[k], i] * p.p["detour_factor"] / p.p["truck_speed"]
                finish = max(arrival, c["ready_time"]) + c["service_time"]
                return max(0, finish - c["due_time"]) * 100 + finish + loads[k] * 0.02
            k = min(choices, key=score)
            pairs[self.index[i]] = k
            clocks[k] = max(clocks[k] + p.dist[tails[k], i] / p.p["truck_speed"], c["ready_time"]) + c["service_time"]
            tails[k], loads[k] = i, loads[k] + c["demand"]
        return Genome(tuple(order), modes, tuple(pairs),
                      tuple(rng.randrange(len(self.site_ids)) if rng.random() < .2 else 0 for _ in order),
                      tuple(rng.choice((0.0, .25, .75)) for _ in order))

    def offspring(self, a, b, rng):
        n = len(a.order)
        if n > 1:
            left, right = sorted(rng.sample(range(n + 1), 2))
            block = a.order[left:right]
            used = set(block)
            remaining = [i for i in b.order if i not in used]
            order = remaining[:left] + list(block) + remaining[left:]
            if rng.random() < .8:
                i, j = sorted(rng.sample(range(n), 2))
                op = rng.randrange(3)
                if op == 0:
                    order[i], order[j] = order[j], order[i]
                elif op == 1:
                    order[i:j+1] = reversed(order[i:j+1])
                else:
                    order.insert(j, order.pop(i))
        else:
            order = list(a.order)
        genes = []
        for ga, gb in zip((a.modes, a.pairs, a.sites, a.charges),
                          (b.modes, b.pairs, b.sites, b.charges)):
            genes.append([x if rng.random() < .5 else y for x, y in zip(ga, gb)])
        for idx, customer in enumerate(self.problem.ids):
            if rng.random() < 1 / max(1, n):
                genes[0][idx] = not genes[0][idx]
            if rng.random() < 2 / max(1, n):
                genes[1][idx] = rng.randrange(self.problem.n_pairs)
            if rng.random() < 1 / max(1, n):
                genes[2][idx] = rng.randrange(len(self.site_ids))
            if rng.random() < 1 / max(1, n):
                genes[3][idx] = rng.choice((0.0, .25, .5, 1.0))
            genes[0][idx] = customer in self.problem.forced or (customer in self.problem.eligible and genes[0][idx])
        return Genome(tuple(order), *(tuple(g) for g in genes))

    def decode(self, genome):
        p = self.problem
        assigned = [[] for _ in range(p.n_pairs)]
        loads = [0.0]*p.n_pairs
        # Repair overloaded pair assignments by placing the parcel in another
        # pair with spare capacity. Remaining excess stays a constraint violation.
        for i in genome.order:
            idx, demand = self.index[i], p.customers[i]["demand"]
            k = genome.pairs[idx]
            if loads[k] + demand > p.capacity:
                available = [v for v in range(p.n_pairs) if loads[v] + demand <= p.capacity]
                k = min(available or range(p.n_pairs), key=lambda v: loads[v])
            loads[k] += demand
            assigned[k].append(i)
        routes = []
        for k, customers in enumerate(assigned):
            nodes, segments, position = [0], [], 0
            while position < len(customers):
                i = customers[position]
                idx = self.index[i]
                is_drone = i in p.forced or (i in p.eligible and genome.modes[idx])
                next_id = customers[position+1] if position+1 < len(customers) else None
                next_truck = (next_id is not None and next_id not in p.forced and
                              not (next_id in p.eligible and genome.modes[self.index[next_id]]))
                if is_drone:
                    site = self.site_ids[genome.sites[idx]]
                    if site is not None:
                        target, consume = site, 1
                    elif next_truck:
                        target, consume = next_id, 2
                    else:
                        # Consecutive sorties need distinct consecutive segments;
                        # flexible stops may repeat, customer service may not.
                        target = min(p.flex, key=lambda f: p.dist[nodes[-1], f] + p.dist[i, f]) if p.flex else 0
                        consume = 1
                    segments.append(dict(type="drone", **{"from": nodes[-1]}, to=target,
                                         drone_customer=i, charge_fraction=genome.charges[idx]))
                else:
                    target, consume = i, 1
                    segments.append(dict(type="truck", **{"from": nodes[-1]}, to=target))
                nodes.append(target)
                position += consume
            segments.append(dict(type="truck", **{"from": nodes[-1]}, to=0))
            nodes.append(0)
            routes.append(dict(pair_id=k+1, truck_route=nodes, segments=segments))
        return p.simulate(routes, schedule=True)
