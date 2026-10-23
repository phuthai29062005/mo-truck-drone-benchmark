"""NSGA-II, NSGA-III and MOEA/D with shared constrained route operators."""

import math
import random
import time
from dataclasses import dataclass

from .encoding import Encoding


@dataclass
class Individual:
    genome: object
    evaluation: object

    @property
    def f(self):
        return self.evaluation.objectives

    @property
    def cv(self):
        return self.evaluation.violation


def dominates(a, b):
    if a.cv != b.cv:
        return a.cv < b.cv
    return all(x <= y for x, y in zip(a.f, b.f)) and any(x < y for x, y in zip(a.f, b.f))


def nondominated_sort(pop):
    counts, dominated = [0]*len(pop), [[] for _ in pop]
    for i, a in enumerate(pop):
        for j in range(i+1, len(pop)):
            if dominates(a, pop[j]):
                dominated[i].append(j)
                counts[j] += 1
            elif dominates(pop[j], a):
                dominated[j].append(i)
                counts[i] += 1
    front = [i for i, c in enumerate(counts) if c == 0]
    result = []
    while front:
        result.append(front)
        nxt = []
        for i in front:
            for j in dominated[i]:
                counts[j] -= 1
                if counts[j] == 0:
                    nxt.append(j)
        front = nxt
    return result


def crowding(pop, front):
    distances = {i: 0.0 for i in front}
    for m in range(2):
        ordered = sorted(front, key=lambda i: pop[i].f[m])
        span = pop[ordered[-1]].f[m] - pop[ordered[0]].f[m]
        if span <= 1e-12:
            continue
        distances[ordered[0]] = distances[ordered[-1]] = math.inf
        for prev, i, nxt in zip(ordered, ordered[1:], ordered[2:]):
            distances[i] += (pop[nxt].f[m] - pop[prev].f[m]) / span
    return distances


def directions(n):
    return [(i / (n-1), 1 - i / (n-1)) for i in range(n)]


def normalize(points):
    """NSGA-III ideal shift, ASF extremes and hyperplane intercepts (2D).

    Degenerate extremes/intercepts fall back to the componentwise maxima.
    """
    ideal = [min(f[m] for f in points) for m in range(2)]
    shifted = [tuple(f[m] - ideal[m] for m in range(2)) for f in points]
    extremes = [min(shifted, key=lambda f: max(f[m] / (1 if m == axis else 1e-6)
                                              for m in range(2))) for axis in range(2)]
    (a, b), (c, d) = extremes
    det = a*d - b*c
    intercepts = [max(f[m] for f in shifted) for m in range(2)]
    if abs(det) > 1e-12:
        coefficients = [(d-b)/det, (a-c)/det]
        if all(x > 1e-12 and math.isfinite(x) for x in coefficients):
            intercepts = [1/x for x in coefficients]
    return [tuple(f[m] / max(intercepts[m], 1e-12) for m in range(2)) for f in shifted]


def survival(pop, size, algorithm, rng):
    selected = []
    for front in nondominated_sort(pop):
        if len(selected) + len(front) <= size:
            selected.extend(front)
            if len(selected) == size:
                break
        else:
            if algorithm == "NSGA-II":
                dist = crowding(pop, front)
                selected.extend(sorted(front, key=lambda i: dist[i], reverse=True)[:size-len(selected)])
            else:
                pool = selected + front
                normalized = normalize([pop[i].f for i in pool])
                refs = directions(size)
                association = {}
                for i, f in zip(pool, normalized):
                    distances = [abs(f[0]*v[1] - f[1]*v[0]) / math.hypot(*v) for v in refs]
                    r = min(range(size), key=distances.__getitem__)
                    association[i] = (r, distances[r])
                counts = [0]*size
                candidates = [[] for _ in refs]
                for i in selected:
                    counts[association[i][0]] += 1
                for i in front:
                    candidates[association[i][0]].append(i)
                while len(selected) < size:
                    active = [r for r in range(size) if candidates[r]]
                    least = min(counts[r] for r in active)
                    r = rng.choice([r for r in active if counts[r] == least])
                    chosen = (min(candidates[r], key=lambda i: association[i][1]) if counts[r] == 0
                              else rng.choice(candidates[r]))
                    selected.append(chosen)
                    candidates[r].remove(chosen)
                    counts[r] += 1
            break
    return [pop[i] for i in selected]


def optimize(problem, algorithm="NSGA-II", population_size=100,
             max_evaluations=500000, time_limit=600.0, seed=42):
    if algorithm not in ("NSGA-II", "NSGA-III", "MOEA/D"):
        raise ValueError("Unknown algorithm")
    if population_size < 2 or max_evaluations < population_size:
        raise ValueError("population_size >= 2 and max_evaluations >= population_size required")
    if time_limit <= 0 or not math.isfinite(time_limit):
        raise ValueError("time_limit must be finite and positive")
    started, rng, encoding = time.perf_counter(), random.Random(seed), Encoding(problem)
    errors = problem.preflight()
    if errors:
        return dict(status="infeasible_precheck", diagnostics=errors, pareto_front=[],
                    n_evaluations=0, runtime_seconds=time.perf_counter()-started)
    archive, evaluations, best = [], 0, None

    def evaluate(genome):
        nonlocal evaluations, best, archive
        individual = Individual(genome, encoding.decode(genome))
        evaluations += 1
        if best is None or individual.cv < best.cv:
            best = individual
        if individual.cv == 0:
            if not any(a.f == individual.f or dominates(a, individual) for a in archive):
                archive = [a for a in archive if not dominates(individual, a)] + [individual]
        return individual

    def remaining():
        return evaluations < max_evaluations and time.perf_counter()-started < time_limit

    pop = []
    for i in range(population_size):
        if not remaining():
            break
        pop.append(evaluate(encoding.initial(rng, i)))
    generations = 0
    if algorithm == "MOEA/D" and len(pop) > 1:
        refs = directions(len(pop))
        neighbors = [sorted(range(len(pop)), key=lambda j: sum((a-b)**2 for a, b in zip(w, refs[j])))
                     [:min(20, len(pop))] for w in refs]
        ideal = [min(a.f[m] for a in pop) for m in range(2)]
        while remaining():
            order = list(range(len(pop)))
            rng.shuffle(order)
            for i in order:
                if not remaining():
                    break
                a, b = rng.sample(neighbors[i], 2)
                child = evaluate(encoding.offspring(pop[a].genome, pop[b].genome, rng))
                ideal = [min(ideal[m], child.f[m]) for m in range(2)]
                # Original Tchebycheff decomposition, zero weights replaced
                # by a small positive value; feasibility precedes scalar fitness.
                for j in neighbors[i]:
                    def scalar(x):
                        return max(max(w, 1e-6) * abs(f-z) for w, f, z in zip(refs[j], x.f, ideal))
                    if child.cv < pop[j].cv or (child.cv == pop[j].cv and scalar(child) <= scalar(pop[j])):
                        pop[j] = child
            generations += 1
    elif algorithm != "MOEA/D":
        while remaining():
            ranks, distances = {}, {}
            for rank, front in enumerate(nondominated_sort(pop)):
                ranks.update({i: rank for i in front})
                distances.update(crowding(pop, front))
            def tournament():
                a, b = rng.randrange(len(pop)), rng.randrange(len(pop))
                ka = (ranks[a], -distances[a] if algorithm == "NSGA-II" else 0)
                kb = (ranks[b], -distances[b] if algorithm == "NSGA-II" else 0)
                return pop[a if ka < kb or (ka == kb and rng.random() < .5) else b]
            offspring = []
            while len(offspring) < population_size and remaining():
                a, b = tournament(), tournament()
                offspring.append(evaluate(encoding.offspring(a.genome, b.genome, rng)))
            pop = survival(pop + offspring, len(pop), algorithm, rng)
            generations += 1
    front = []
    for i, a in enumerate(sorted(archive, key=lambda a: a.f), 1):
        front.append(dict(id=i, **a.evaluation.solution))
    result = dict(status="ok" if front else "no_feasible_solution", pareto_front=front,
                  n_evaluations=evaluations, generations=generations,
                  runtime_seconds=time.perf_counter()-started)
    if not front and best is not None:
        result.update(best_constraint_violation=best.cv, diagnostics=best.evaluation.errors)
    return result
