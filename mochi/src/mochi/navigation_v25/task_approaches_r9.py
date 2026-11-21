"""Conservative transit plus an oriented, geometrically checked task approach."""
from dataclasses import replace
import copy
import math
from types import SimpleNamespace

import mujoco
import numpy as np

from mochi.balanced.sequence import PhysicalStop
from mochi.navigation_v25.engine import observation, decision
from mochi.navigation_v25.navigation import NavigationParameters, navigate
from mochi.navigation_v25.planner import PROFILES, plan
from mochi.navigation_v23.world import bounds
from mochi.balanced.onnx_walk import HubWalker as NavigationWalker


def pose_corridor_clear(w, start, goal, turn_at_goal=False):
    """Offline kinematics only. The real simulator state is never reassigned."""
    scratch = mujoco.MjData(w.m)
    scratch.qpos[:] = w.d.qpos
    view = SimpleNamespace(m=w.m, d=scratch)
    bearing = math.atan2(goal[1] - start[1], goal[0] - start[0]) if math.dist(start[:2], goal[:2]) > .001 else goal[2]
    for point in np.linspace(start[:2], goal[:2], max(2, int(math.dist(start[:2], goal[:2]) / .01) + 2)):
        yaws = [goal[2] - math.radians(9), goal[2], goal[2] + math.radians(9)]
        if turn_at_goal:
            yaws = [bearing - math.radians(9), bearing, bearing + math.radians(9)]
            if math.dist(point, goal[:2]) < .04:
                turn = (goal[2] - bearing + math.pi) % (2 * math.pi) - math.pi
                yaws += np.linspace(bearing, bearing + turn, max(3, int(abs(turn) / .12) + 2)).tolist()
        if math.dist(point, start[:2]) < .04:
            departure_heading = bearing if turn_at_goal else goal[2]
            first_turn = (departure_heading - start[2] + math.pi) % (2 * math.pi) - math.pi
            yaws += np.linspace(start[2], start[2] + first_turn, max(3, int(abs(first_turn) / .12) + 2)).tolist()
        for yaw in yaws:
            scratch.qpos[:2] = point
            scratch.qpos[3:7] = [math.cos(yaw / 2), 0., 0., math.sin(yaw / 2)]
            mujoco.mj_forward(w.m, scratch)
            for contact in scratch.contact:
                a, b = int(contact.geom1), int(contact.geom2)
                ra, rb = int(w.m.geom_bodyid[a]) in w.robot_bodies, int(w.m.geom_bodyid[b]) in w.robot_bodies
                if ra == rb:
                    continue
                robot, fixture = (a, b) if ra else (b, a)
                name = mujoco.mj_id2name(w.m, mujoco.mjtObj.mjOBJ_BODY, int(w.m.geom_bodyid[robot])) or ''
                if name.endswith('ankle_roll_link') and fixture == w.id('geom', 'desk'):
                    continue
                if contact.dist < .001:
                    return False
            for side in ['left', 'right']:
                body = w.id('body', side + '_ankle_roll_link')
                for gid in range(w.m.ngeom):
                    if int(w.m.geom_bodyid[gid]) != body or not w.m.geom_contype[gid]:
                        continue
                    low, high = bounds(view, gid)
                    # Reserve horizontal foot-swing space, rather than using a
                    # yaw-invariant arm envelope beside an intentional hand task.
                    low[:2] -= .012
                    high[:2] += .012
                    if np.any(low[:2] < [-.60, -.40]) or np.any(high[:2] > [.60, .40]):
                        return False
                    for obstacle in w.obstacles():
                        # Rotated footprints and elevated objects have empty
                        # corners in their AABBs. Query actual 3D primitives.
                        gap = mujoco.mj_geomDistance(w.m, scratch, gid, obstacle['geom_id'], .05, None)
                        if gap < .014:
                            return False
    return True


def reachable_hand(w, task, goal):
    """Solve on a planning copy, never the live MuJoCo state."""
    from mochi.curriculum.world import PAD_RADIUS
    from mochi.navigation_tasks_v24.relative_laptop import laptop_surface
    proxy = copy.copy(w)
    proxy.d, proxy.viz = copy.copy(w.d), mujoco.MjData(w.m)
    proxy.d.qpos[:2] = goal[:2]
    proxy.d.qpos[3:7] = [math.cos(goal[2] / 2), 0., 0., math.sin(goal[2] / 2)]
    proxy.task = task
    mujoco.mj_forward(w.m, proxy.d)
    if task == 'laptop':
        point, normal = laptop_surface(w, w.value(task), .15, .263, .014)
    elif task == 'drawer':
        normal = np.array([0., -1., 0.])
        point = w.d.xpos[w.id('body', 'drawer')] + [.008, 0., .010] + normal * (.0025 + PAD_RADIUS + .014)
    else:
        normal = np.array([math.cos(math.pi-.25), math.sin(math.pi-.25), 0.])
        point = w.d.xpos[w.id('body', 'globe')] + normal * (.058 + PAD_RADIUS + .014)
    side = 'left' if task == 'laptop' else 'right'
    q = proxy.ik(side, point, normal, from_home=True)
    proxy.viz.qpos[proxy.arm[side]['qs']] = q
    mujoco.mj_forward(w.m, proxy.viz)
    return float(np.linalg.norm(proxy.viz.site_xpos[proxy.arm[side]['tip']] - point))


def task_pose(w, task):
    original = w.station_goal(task)
    offsets = [(0., 0.), (.005, 0.), (.010, 0.), (.015, 0.), (.020, 0.), (.010, -.010)] if task == 'laptop' else [(0., 0.)]
    for dx, dy in offsets:
        goal = [original[0] + dx, original[1] + dy, original[2]]
        if pose_corridor_clear(w, goal, goal) and reachable_hand(w, task, goal) <= .006:
            w.task_poses[task] = goal
            return goal
    raise PhysicalStop('no-clear-reachable-task-pose:' + task)


def candidate_approach(w, goal):
    obstacles, envelope = w.obstacles(), w.envelope()
    if not pose_corridor_clear(w, goal, goal):
        raise PhysicalStop('task-pose-kinematically-obstructed')
    current = [*w.d.qpos[:2].tolist(), w.yaw()]
    if math.dist(current[:2], goal[:2]) <= .30:
        for mode in ['turn_at_goal', 'fixed_heading']:
            if pose_corridor_clear(w, current, goal, mode == 'turn_at_goal'):
                return {'pose': goal, 'alignment_mode': mode, 'direct_fine': True}
    forward = np.array([math.cos(goal[2]), math.sin(goal[2])])
    lateral = np.array([-forward[1], forward[0]])
    candidates = []
    for back in [.08, .12, .16, .20, .24, .04, 0.]:
        for side in [0., .06, -.06, .10, -.10, .16, -.16, .20, -.20]:
            point = np.asarray(goal[:2]) - back * forward + side * lateral
            if abs(point[0]) > .58 or abs(point[1]) > .38:
                continue
            staging = [*point.tolist(), goal[2]]
            candidates_for_pose = [plan(w.d.qpos[:2], staging, obstacles, envelope, code)
                for code in ['planner', 'buffered', 'direct']]
            feasible = [(tier, p) for tier, p in enumerate(candidates_for_pose) if p['feasible']]
            if not feasible:
                continue
            tier, path = feasible[0]
            for mode in ['turn_at_goal', 'fixed_heading']:
                if pose_corridor_clear(w, staging, goal, mode == 'turn_at_goal'):
                    candidates.append((tier, path['length_m'] + back + (1 if mode == 'turn_at_goal' else 3) * abs(side),
                        {'pose': staging, 'alignment_mode': mode}))
                    break
    if not candidates:
        raise PhysicalStop('no-validated-task-approach')
    # Choose a broadly reachable staging pose before shortening its final
    # approach. A narrow goal must not force a minimum-margin whole-desk route.
    return min(candidates, key=lambda c: (c[0], c[1]))[2]


def transit(w, goal, task, choose=None, fine_goal=None, fine_mode='fixed_heading', direct_fine=False):
    w.globe_foot_feedback = task == 'globe'
    # The native 29-DOF policy otherwise resumes arm swing just after recovery.
    # Keep those same joint actuators at their recovered commands beside props.
    if not isinstance(w.walker, NavigationWalker):
        w.walker = NavigationWalker(w)
    envelope, obstacles = w.envelope(), w.obstacles()
    plans = {name: plan(w.d.qpos[:2], goal, obstacles, envelope, name) for name in PROFILES}
    observed = observation(SimpleNamespace(d=w.d, yaw=w.yaw, layout={'goal': goal}), envelope, obstacles, plans)
    default = next((name for name in ['planner', 'buffered', 'wide_fast', 'direct'] if plans[name]['feasible']), 'planner')
    if direct_fine:
        observed = {'domain': 'task_alignment', 'goal': goal,
            'method': 'Shared oriented collision check including foot-swing allowance; no neural route decision.'}
        picked = {'action': 'validated_fine', 'source': 'shared oriented task-alignment primitive; no learned route choice'}
        action = 'buffered'
        path = {'feasible': True, 'points': [w.d.qpos[:2].tolist(), goal[:2]]}
    else:
        picked = choose('navigation', task, observed, decision(observed)) if choose else {
            'action': default, 'source': 'collision-aware planner with declared bounded-margin feasibility fallback'}
        action = picked['action']
        path = plans[action]
    w.decisions.append({'t': float(w.d.time), 'observation': observed, **picked})
    if not path['feasible']:
        raise PhysicalStop('no-geometric-route:' + task)
    profile = PROFILES[action]
    parameters = NavigationParameters(yaw_gain=2.4, max_yaw_rate=profile['yaw_rate'], forward_gain=1.6,
        alignment_gain=2.4 if task == 'globe' else 1.15, near_distance=.014)
    if direct_fine and fine_mode == 'fixed_heading':
        parameters = replace(parameters, near_distance=math.dist(w.d.qpos[:2], goal[:2]) + .02)
    started = float(w.d.time)
    rows = []
    w.raised_native_swing, w.swing_lift_reference = True, .008 if task == 'globe' else .0065
    w.swing_forward_reference, w.swing_joint_residual_limit = 0., .14 if task == 'globe' else .10
    w.efficiency_segment = 'flat_transit'
    try:
        points = path['points'][1:]
        for index, point in enumerate(points):
            final = index == len(points) - 1
            heading = goal[2] if final else math.atan2(points[index + 1][1] - point[1], points[index + 1][0] - point[0])
            rows.append(navigate(w, [*point, heading], stop=True, speed=profile['speed'],
                parameters=parameters, label=task + '-transit-' + str(index)))
        if fine_goal:
            # The turn is completed in the disk-clear staging space. The
            # checked narrow approach keeps that heading through real control.
            near = math.dist(goal[:2], fine_goal[:2]) + .02 if fine_mode == 'fixed_heading' else .028
            rows.append(navigate(w, fine_goal, stop=True, speed=min(.075, profile['speed']),
                parameters=replace(parameters, near_distance=near), label=task + '-object-relative-pose'))
    finally:
        w.raised_native_swing = False
        w.navigation_legs.append({'task': task, 'start_t': started, 'end_t': float(w.d.time),
            'goal': goal, 'fine_goal': fine_goal, 'fine_mode': fine_mode, 'action': picked['action'], 'plans': plans, 'arrivals': rows})
    return rows
