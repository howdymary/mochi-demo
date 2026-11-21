"""Collision-aware disk-envelope planning with continuous segment checks."""
import heapq
import math

import numpy as np

PROFILES = {
    'direct': {'margin': .004, 'risk': .0, 'speed': .100, 'yaw_rate': 1.0},
    'buffered': {'margin': .016, 'risk': .012, 'speed': .075, 'yaw_rate': .75},
    'wide_fast': {'margin': .016, 'risk': .012, 'speed': .100, 'yaw_rate': .75},
    'planner': {'margin': .018, 'risk': .025, 'speed': .075, 'yaw_rate': .75},
}


def clearance(points, obstacles):
    points = np.atleast_2d(points)
    distance = np.minimum(.6 - abs(points[:, 0]), .4 - abs(points[:, 1]))
    for obstacle in obstacles:
        low, high = np.asarray(obstacle['minimum'][:2]), np.asarray(obstacle['maximum'][:2])
        outside = np.maximum(np.maximum(low - points, points - high), 0.)
        d = np.linalg.norm(outside, axis=1)
        distance = np.minimum(distance, d)
    return distance


def segment_clear(a, b, obstacles, radius):
    n = max(2, int(math.dist(a, b) / .003) + 2)
    return bool(np.min(clearance(np.linspace(a, b, n), obstacles)) >= radius)


def plan(start, goal, obstacles, envelope, code):
    p = PROFILES[code]
    radius = envelope['planning_radius_m'] + p['margin']
    resolution = .01
    xs, ys = np.arange(-.58, .581, resolution), np.arange(-.38, .381, resolution)
    xx, yy = np.meshgrid(xs, ys, indexing='ij')
    distances = clearance(np.c_[xx.ravel(), yy.ravel()], obstacles).reshape(xx.shape)
    free = distances >= radius
    node = lambda xy: (int(round((xy[0] - xs[0]) / resolution)), int(round((xy[1] - ys[0]) / resolution)))
    source, target = node(start), node(goal)
    if not (free[source] and free[target]) or min(clearance([list(start[:2]), list(goal[:2])], obstacles)) < radius:
        return {'feasible': False, 'reason': 'start_or_goal_clearance', 'profile': code, 'radius_m': radius}
    queue, costs, parent = [(0., source)], {source: 0.}, {}
    directions = [(i, j) for i in [-1, 0, 1] for j in [-1, 0, 1] if i or j]
    while queue:
        _, current = heapq.heappop(queue)
        if current == target:
            break
        for dx, dy in directions:
            nxt = current[0] + dx, current[1] + dy
            if not (0 <= nxt[0] < len(xs) and 0 <= nxt[1] < len(ys)) or not free[nxt]:
                continue
            if dx and dy and not (free[current[0] + dx, current[1]] and free[current[0], current[1] + dy]):
                continue
            cost = costs[current] + resolution * math.hypot(dx, dy) * (1 + p['risk'] / max(.004, distances[nxt] - radius + .01))
            if cost >= costs.get(nxt, float('inf')):
                continue
            costs[nxt], parent[nxt] = cost, current
            heapq.heappush(queue, (cost + resolution * math.dist(nxt, target), nxt))
    if target not in costs:
        return {'feasible': False, 'reason': 'no_collision_free_corridor', 'profile': code, 'radius_m': radius}
    nodes, current = [target], target
    while current != source:
        current = parent[current]
        nodes.append(current)
    nodes.reverse()
    points = [list(start[:2])] + [[float(xs[i]), float(ys[j])] for i, j in nodes] + [list(goal[:2])]
    # Greedy visibility simplification preserves the full inflated envelope.
    simple, i = [points[0]], 0
    while i < len(points) - 1:
        j = len(points) - 1
        while j > i + 1 and not segment_clear(points[i], points[j], obstacles, radius):
            j -= 1
        if not segment_clear(points[i], points[j], obstacles, radius):
            return {'feasible': False, 'reason': 'grid_to_continuous_connection', 'profile': code, 'radius_m': radius}
        simple.append(points[j])
        i = j
    samples = np.concatenate([np.linspace(a, b, max(2, int(math.dist(a, b) / .004) + 2)) for a, b in zip(simple, simple[1:])])
    return {'feasible': True, 'profile': code, 'radius_m': radius, 'points': simple,
        'length_m': sum(math.dist(a, b) for a, b in zip(simple, simple[1:])),
        'minimum_envelope_clearance_m': float(np.min(clearance(samples, obstacles)) - envelope['planning_radius_m']),
        'turns': max(0, len(simple) - 2), 'parameters': p,
        'scope': 'Geometrically feasible conservative swept disk; successful dynamic execution is evaluated separately.'}
