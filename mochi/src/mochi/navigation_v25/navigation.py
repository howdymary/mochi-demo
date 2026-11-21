"""V25 actuator navigation with direction-preserving final alignment."""
import math
from dataclasses import dataclass

import numpy as np

from mochi.curriculum.world import wrap
from mochi.balanced.sequence import PhysicalStop, average_velocity
from mochi.balanced.onnx_walk import HubWalker, HoldWalker
from mochi.balanced.balance import support


@dataclass(frozen=True)
class NavigationParameters:
    yaw_gain: float = 1.8
    max_yaw_rate: float = .6
    turn_threshold_degrees: float = 35.
    lateral_limit: float = .004
    alignment_lateral_limit: float = .012
    near_distance: float = .035
    parked_arms: bool = False
    forward_gain: float = .7
    alignment_gain: float = .6


def command(position, yaw, goal, line_heading, speed, parameters, aligning=False):
    """Body-frame velocity command, never a physical pose assignment."""
    delta = np.asarray(goal[:2]) - position
    distance = float(np.linalg.norm(delta))
    bearing = math.atan2(delta[1], delta[0]) if distance > .001 else line_heading
    desired = goal[2] if aligning else bearing
    error = wrap(desired - yaw)
    turn = float(np.clip(error * parameters.yaw_gain, -parameters.max_yaw_rate, parameters.max_yaw_rate))
    if abs(error) > math.radians(parameters.turn_threshold_degrees):
        return (0., 0., turn), 'turn-to-task' if aligning else 'turn-to-path', desired
    c, s = math.cos(yaw), math.sin(yaw)
    forward, lateral = np.array([[c, s], [-s, c]]) @ delta
    if aligning:
        # Independent clipping can turn an intended leftward diagonal into a
        # rightward curve. Scale the whole body-frame vector by one factor.
        vector = np.array([forward, lateral]) * parameters.alignment_gain
        scale = min(1., (speed if vector[0] >= 0 else .008) / max(abs(vector[0]), 1e-9),
            parameters.alignment_lateral_limit / max(abs(vector[1]), 1e-9))
        vector *= scale * max(0., math.cos(error)) ** 2
        return (float(vector[0]), float(vector[1]), turn), 'task-alignment', desired
    vx = float(np.clip(forward * parameters.forward_gain, -.008 if distance < parameters.near_distance else 0., speed))
    if not aligning and forward > .012:
        vx = max(vx, .012)
    vx *= max(0., math.cos(error)) ** 2
    lateral_limit = parameters.alignment_lateral_limit if aligning else parameters.lateral_limit
    vy = float(np.clip(lateral * parameters.alignment_gain, -lateral_limit, lateral_limit))
    return (vx, vy, turn), 'task-alignment' if aligning else 'walk-forward', desired


def navigate(w, goal, *, timeout=45., stop=True, speed=.055,
             position_tolerance=.012, label='waypoint', parameters=None):
    p = parameters or NavigationParameters()
    start = float(w.d.time)
    w.task = None
    w.phase = 'walk'
    if not isinstance(w.walker, HubWalker):
        w.walker = HubWalker(w)
    else:
        w.walker.resume()
    if p.parked_arms:
        w.walker.control_arms = False
        for arm in w.arm.values():
            w.d.ctrl[arm['acts']] = arm['rest']
    origin = w.d.qpos[:2].copy()
    line = np.array(goal[:2]) - origin
    line_heading = math.atan2(line[1], line[0]) if np.linalg.norm(line) > .001 else goal[2]
    w.path_heading, w.path_origin = line_heading, origin
    holding, stable, phase = False, 0., None
    aligning = False
    samples = []
    next_sample = start
    while w.d.time - start < timeout:
        distance = math.dist(w.d.qpos[:2], goal[:2])
        error = abs(wrap(goal[2] - w.yaw()))
        if not stop and distance < .018:
            break
        # Latch the final-heading phase. Gait sway must not alternate a
        # nearly opposite travel bearing and final task heading every step.
        if distance < p.near_distance:
            aligning = True
        elif distance > max(.055, 2 * p.near_distance):
            aligning = False
        if holding and (distance > position_tolerance or error >= math.radians(9)):
            w.walker = HubWalker(w)
            holding, stable = False, 0.
        near = distance < position_tolerance
        considering = stop and not holding and near and error < math.radians(9)
        supported = False
        if considering:
            balance = support(w)
            supported = (balance['capture_margin_m'] is not None and balance['capture_margin_m'] >= .001
                and all(w.foot_touching(side) for side in ['left', 'right'])
                and all(load > .2 for load in w.loads().values()))
        if (considering and supported and np.linalg.norm(average_velocity(w)) < .015
                and np.linalg.norm(w.d.qvel[:2]) < .08):
            w.walker.hold()
            holding = True
            w.events.append({'t': float(w.d.time), 'phase': 'supported-capture', 'station': label})
        if holding:
            w.phase = 'settle'
            w.step()
            good = (all(load > .05 for load in w.loads().values()) and error < math.radians(9)
                and distance <= position_tolerance)
            stable = stable + w.m.opt.timestep if good else 0.
            if stable >= .4:
                if isinstance(w.walker, HubWalker):
                    w.walker = HoldWalker(w)
                    stable = 0.
                    continue
                break
        else:
            velocity, current_phase, desired = command(w.d.qpos[:2], w.yaw(), goal,
                line_heading, speed, p, aligning=stop and aligning)
            if current_phase != phase:
                w.events.append({'t': float(w.d.time), 'phase': current_phase,
                    'station': label, 'heading_goal_rad': desired, 'measured_yaw_rad': w.yaw()})
                phase = current_phase
            w.phase = 'turn' if current_phase.startswith('turn') else 'walk'
            w.step(velocity)
            if w.d.time >= next_sample:
                actual = average_velocity(w, .25)
                samples.append({'t': float(w.d.time), 'phase': current_phase,
                    'yaw_rad': w.yaw(), 'desired_yaw_rad': desired, 'command': list(velocity),
                    'root': w.d.qpos[:3].tolist(), 'cycle_averaged_velocity_xy': actual.tolist()})
                next_sample = float(w.d.time) + .04
    success = (not stop and math.dist(w.d.qpos[:2], goal[:2]) < .018) or (stable >= .4
        and math.dist(w.d.qpos[:2], goal[:2]) <= position_tolerance
        and abs(wrap(goal[2] - w.yaw())) < math.radians(9))
    if not hasattr(w, 'navigation_traces'):
        w.navigation_traces = []
    w.navigation_traces.append({'label': label, 'goal': list(goal), 'samples': samples})
    row = {'label': label, 'goal': list(goal), 'success': bool(success),
        'duration_s': float(w.d.time) - start, 'position_error_mm': math.dist(w.d.qpos[:2], goal[:2]) * 1000,
        'heading_error_degrees': math.degrees(abs(wrap(goal[2] - w.yaw()))),
        'root': w.d.qpos[:3].tolist(), 'dwell_s': stable,
        'navigation': 'latched final-heading alignment with geometric exit hysteresis and position-valid supported dwell', 'loads_n': w.loads()}
    w.events.append({'t': float(w.d.time), 'phase': 'arrival', **row})
    if not success:
        raise PhysicalStop('directional-navigation-timeout:' + label)
    return row
