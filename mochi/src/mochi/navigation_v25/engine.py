"""Complete physical navigation attempts; no root or foot pose animation."""
import hashlib
import json
import math
import time

import numpy as np

from mochi.balanced.onnx_walk import HubWalker
from mochi.balanced.sequence import PhysicalStop
from mochi.curriculum.world import wrap
from mochi.navigation_v25.navigation import NavigationParameters, navigate
from mochi.navigation_v23.navigation import travel_metrics
from mochi.navigation_v25.planner import PROFILES, plan, clearance
from mochi.navigation_tasks_v24.world import RelativeTaskWorld as NavigationWorld

ACTIONS = ['direct', 'buffered', 'wide_fast']


def inspect(layout, seed):
    w = NavigationWorld(layout, seed, False)
    envelope, obstacles = w.envelope(), w.obstacles()
    plans = {name: plan(w.d.qpos[:2], layout['goal'], obstacles, envelope, name) for name in [*ACTIONS, 'planner']}
    return w, envelope, obstacles, plans


def observation(w, envelope, obstacles, plans, memories=None):
    root, yaw = w.d.qpos[:2], w.yaw()
    rotation = np.array([[math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)]])
    relative = lambda xy: np.round(rotation @ (np.asarray(xy[:2])-root)*1000, 1).tolist()
    options = {}
    for name in ACTIONS:
        path = plans[name]
        entry = {'feasible': path['feasible'], 'parameters': PROFILES[name]}
        if path['feasible']:
            points = path['points']
            bearings = [math.atan2(b[1]-a[1], b[0]-a[0]) for a,b in zip(points,points[1:])]
            turns = [wrap(b-a) for a,b in zip([yaw]+bearings, bearings+[w.layout['goal'][2]])]
            entry.update(length_mm=round(path['length_m']*1000,1),
                minimum_planned_clearance_mm=round(path['minimum_envelope_clearance_m']*1000,1),
                turns_degrees=[round(math.degrees(v),1) for v in turns],
                waypoints_body_mm=[relative(point) for point in points])
        options[name]=entry
    return {'domain':'navigation', 'information':'privileged simulation geometry; no sensors',
        'target_body_mm':relative(w.layout['goal']),
        'target_heading_degrees':round(math.degrees(wrap(w.layout['goal'][2]-yaw)),1),
        'robot_planning_radius_mm':round(envelope['planning_radius_m']*1000,1),
        'obstacles':[{'centre_body_mm':relative((np.asarray(o['minimum'])+o['maximum'])/2),
            'size_mm':np.round((np.asarray(o['maximum'])-o['minimum'])*1000,1).tolist()} for o in obstacles],
        'options':options, 'prior_findings':memories or []}


def decision(observed):
    from tinker_cookbook.recipes.decisions import Decision
    return Decision('Choose a physical navigation profile. Qualification under support, collision, heading and 4.5 mm moving-foot-clearance checks comes first. '
        'Among qualified outcomes minimize measured steps, then time. Narrow margins and speed are separate choices. '
        'A feasible geometric route may still fail physical quality. The native gait is fixed.\nObserved: '+json.dumps(observed,sort_keys=True),
        [(a, a+': '+json.dumps(observed['options'][a],sort_keys=True)) for a in ACTIONS])


def run(layout, seed, action='planner', choose=None, memories=None, record=True):
    wall = time.perf_counter()
    w = NavigationWorld(layout, seed, record)
    w.use_native_stand = True
    envelope, obstacles = w.envelope(), w.obstacles()
    plans = {name: plan(w.d.qpos[:2], layout['goal'], obstacles, envelope, name) for name in [*ACTIONS, 'planner']}
    obs = observation(w, envelope, obstacles, plans, memories)
    selection = choose(obs) if choose else {'action': action, 'source': 'frozen deterministic baseline'}
    if isinstance(selection, str):
        selection = {'action': selection}
    action = selection['action']
    assert action in plans
    path = plans[action]
    initial_hash = hashlib.sha256(np.r_[w.d.qpos, w.d.qvel, w.d.ctrl].tobytes()).hexdigest()
    failures, arrivals, tracking, failure = [], [], [], None
    w.decisions.append({'t': 0., 'observation': obs, **selection})
    try:
        if not path['feasible']:
            raise PhysicalStop('no-geometric-route:' + path['reason'])
        while w.d.time < .4:
            w.step(standing=True)
        w.walker = HubWalker(w)
        w.raised_native_swing, w.swing_lift_reference = True, .006
        w.swing_forward_reference, w.swing_joint_residual_limit = 0., .10
        w.efficiency_segment = 'flat_transit'
        p = PROFILES[action]
        parameters = NavigationParameters(yaw_gain=2.4, max_yaw_rate=p['yaw_rate'], forward_gain=1.6,
            alignment_gain=1.15, near_distance=.028)
        points = path['points'][1:]
        for i, point in enumerate(points):
            final = i == len(points) - 1
            heading = layout['goal'][2] if final else math.atan2(points[i + 1][1] - point[1], points[i + 1][0] - point[0])
            remaining = 120. - float(w.d.time)
            if remaining <= 0:
                raise PhysicalStop('navigation-episode-horizon')
            arrivals.append(navigate(w, [*point, heading], timeout=min(45., remaining),
                stop=True, speed=p['speed'], position_tolerance=.012,
                label='target' if final else 'corridor-' + str(i), parameters=parameters))
    except PhysicalStop as error:
        failure = str(error)
    w.raised_native_swing = False
    episode = w.episode()
    trace = [v for leg in getattr(w, 'navigation_traces', []) for v in leg['samples']]
    for row in w.measurements:
        tracking.append({'t': row['t'], 'root': row['root'], 'clearance_m': float(clearance([row['root'][:2]], obstacles)[0]) - envelope['planning_radius_m']})
    distance = sum(math.dist(a['root'][:2], b['root'][:2]) for a, b in zip(tracking, tracking[1:]))
    balance = episode['balance_metrics']
    footprint = episode['flat_foot_clearance']
    complete = bool(failure is None and arrivals and arrivals[-1]['success'] and not w.fall and not w.invalid_contact)
    checks = {
        'arrival': complete,
        'roll_rms': balance['roll_rms_deg'] is not None and balance['roll_rms_deg'] <= 2.,
        'roll_peak': balance['roll_peak_deg'] is not None and balance['roll_peak_deg'] <= 12.,
        'supported': episode['longest_unsupported_seconds'] <= .06,
        'moving_foot_clearance': footprint['moving_swings_measured'] >= 2 and (footprint['moving_median_peak_m'] or 0.) >= .0045,
        'horizon': episode['duration'] <= 120.01,
    }
    qualified = all(checks.values())
    travel = travel_metrics(trace)
    arm = sum(episode['intertask_arm_joint_travel_rad'].values())
    result = {'study': 'mochi-navigation-v25', 'layout_sha256': layout['layout_sha256'],
        'layout_partition': layout['partition'], 'seed': seed, 'layout': layout,
        'initial_physical_state_sha256': initial_hash, 'mechanics_sha256': w.mechanics_sha256,
        'action': action, 'selection': selection, 'observation': obs, 'plans': plans,
        'complete': complete, 'qualified': qualified, 'checks': checks, 'failure': failure,
        'fall': w.fall, 'invalid_contact': w.invalid_contact, 'arrivals': arrivals,
        'steps': episode['steps'], 'physical_seconds': episode['duration'],
        'executed_distance_m': distance,
        'reference_planned_distance_m': plans['planner'].get('length_m'),
        'excess_distance_m': distance - plans['planner']['length_m'] if complete and plans['planner']['feasible'] else None,
        'distance_scope': 'Raw measured pelvis travel, including gait sway, minus the same geometrically feasible planner reference for every policy on this layout/seed. Dynamic execution success is reported separately.',
        'minimum_envelope_clearance_m': min((v['clearance_m'] for v in tracking), default=None),
        'travel_metrics': travel, 'arm_travel_rad': arm, 'tracking': tracking,
        'envelope': envelope, 'obstacles': obstacles, 'episode': episode,
        'wall_seconds': time.perf_counter() - wall, 'optimizer_updates': selection.get('optimizer_updates', 0),
        'scope': 'One uninterrupted navigation attempt from reset, exact state information, fixed native gait and actuator control.'}
    result['reward'] = (-1_000_000. if not qualified else 1000. - episode['steps']['attempts']
        - .1 * distance - .001 * episode['duration'])
    return result
