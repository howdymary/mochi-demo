"""One continuous physical sequence, gated separately from navigation study A."""
import json
import math
from pathlib import Path
import time

from mochi.balanced.onnx_walk import HubWalker, HoldWalker
from mochi.balanced.sequence import PhysicalStop
from mochi.control_v8.verification import full_success
from mochi.paperfree_v19.objective import qualify
from mochi.smooth_v16.navigation import travel_metrics
from mochi.smooth_v16.policy import WALKS
from mochi.smooth_v16.terrain import clear_and_turn, forward_descent
from mochi.terrain_v12.legs import BASE
from mochi.terrain_v12.sequence import book_leg
from .task_approaches import transit, candidate_approach, task_pose, pose_corridor_clear
from mochi.navigation_tasks_v24.world import RelativeTaskWorld
from mochi.navigation_tasks_v24 import policy


class TaskWorld(RelativeTaskWorld):
    def step(self,*args,**kwargs):
        from .task_lift import SoleFeedbackWalker
        if getattr(self,'globe_foot_feedback',False) and isinstance(self.walker,HubWalker) and not isinstance(self.walker,SoleFeedbackWalker):
            self.walker.__class__=SoleFeedbackWalker
        return super().step(*args,**kwargs)

    def station_goal(self, task):
        if task == 'globe':
            if task in self.task_poses:
                return self.task_poses[task]
            p=self.d.xpos[self.id('body','globe-base')]
            return [float(p[0]-.120),float(p[1]),0.]
        return super().station_goal(task)


def run(layout, seed, choose=None, until='all', capture=None):
    w = TaskWorld(layout, seed, True)
    w.use_native_stand = True
    w.terrain_controller_history, w.navigation_legs = [], []
    started = time.perf_counter()
    arrivals, failure = [], None
    try:
        while w.d.time < .4:
            w.step(standing=True)
        w.walker = HubWalker(w)
        arrivals.extend(transit(w, [-.375, -.225, math.pi / 2], 'book-entry', choose))
        w.efficiency_segment = 'book_ascent'
        w.walker = HoldWalker(w)
        arrivals.append(book_leg(w, 1, {**BASE, **{k: v for k, v in WALKS['W2'].items() if k != 'flat_speed'}}))
        if until == 'ascent':
            return finish(w, layout, seed, arrivals, failure, started, until)
        for task in ['alarm', 'drawer', 'laptop', 'globe']:
            if task == 'drawer':
                book_parameters = {**BASE, **{k: v for k, v in WALKS['W5'].items() if k != 'flat_speed'}}
                arrivals.extend(clear_and_turn(w, book_parameters))
                descent_parameters = {**BASE, **{k: v for k, v in WALKS['W0'].items() if k != 'flat_speed'}}
                arrivals.extend(forward_descent(w, descent_parameters))
                flat_begin = float(w.d.time)
                # Leave the book edge facing down before asking the disk
                # planner to turn. This shared clearance move is engineering.
                exit_goal = [float(w.d.qpos[0]), min(float(w.d.qpos[1]) - .055, -.235), -math.pi / 2]
                current = [*w.d.qpos[:2].tolist(), w.yaw()]
                if not pose_corridor_clear(w, current, exit_goal):
                    raise PhysicalStop('book-exit-corridor-not-clear')
                arrivals.extend(transit(w, exit_goal, 'book-exit-clearance', direct_fine=True))
                if until == 'books':
                    break
            if task != 'alarm':
                if capture:
                    capture(w, 'navigation', task)
                before = flat_begin if task == 'drawer' else float(w.d.time)
                goal = task_pose(w, task)
                staging = candidate_approach(w, goal)
                arrivals.extend(transit(w, staging['pose'], task, choose,
                    fine_goal=None if staging.get('direct_fine') else goal,
                    fine_mode=staging['alignment_mode'], direct_fine=staging.get('direct_fine', False)))
                clearance = w.episode()['flat_foot_clearance']
                swings = [s for s in clearance['swings'] if s['start_t'] >= before and s['category'] in ['flat_transit', 'turning', 'fixture_clearance']]
                from statistics import median
                w.flat_legs.append({'task': task, 'success': True, 'moving_swings': len(swings),
                    'moving_minimum_sole_clearance_m': median(s['peak_minimum_sole_clearance_m'] for s in swings) if swings else None})
            for domain in [task, 'recovery']:
                if capture:
                    capture(w, domain, task)
                default = 'R4' if domain == 'recovery' else {'alarm': 'H0', 'drawer': 'C', 'laptop': 'P5', 'globe': 'G0'}[task]
                observed = policy.observation(w, domain, task)
                picked = choose(domain, task, observed, policy.decision(observed)) if choose else {'action': default, 'source': 'fixed task validation reference'}
                w.decisions.append({'t': float(w.d.time), 'observation': observed, **picked})
                result = policy.execute(w, domain, task, picked['action'])
                if not result['success']:
                    raise PhysicalStop(domain + '-failed:' + task)
        if until == 'all':
            end = float(w.d.time) + .5
            while w.d.time < end:
                w.step()
    except PhysicalStop as error:
        failure = str(error)
    return finish(w, layout, seed, arrivals, failure, started, until)


def finish(w, layout, seed, arrivals, failure, started, until):
    episode = w.episode()
    episode['navigation_legs'] = w.navigation_legs
    complete = bool(until == 'all' and not failure and full_success(episode) and not w.invalid_contact
        and len(w.recoveries) == 4 and all(r['success'] for r in w.recoveries)
        and all(w.foot_touching(s) for s in ['left', 'right'])
        and any(a['label'] == 'book-ascent' and a['success'] for a in arrivals)
        and any(a['label'] == 'book-top-turnaround' and a['success'] for a in arrivals)
        and any(a['label'] == 'book-forward-descent' and a['success'] for a in arrivals)
        and episode['maximum_applied_base_force'] == 0)
    row = {'study': 'mochi-navigation-tasks-v25', 'layout': layout, 'seed': seed,
        'mechanics_sha256': w.mechanics_sha256, 'requested_end': until,
        'complete_sequence_success': complete, 'failure': failure, 'arrivals': arrivals,
        'episode': episode, 'direction_metrics': travel_metrics(w.direction_samples),
        'wall_seconds': time.perf_counter() - started,
        'scope': 'Uninterrupted actuator-driven development attempt, object-relative task primitives. No state restoration within this sequence. Native gait weights fixed.'}
    if until == 'all':
        cfg = json.loads((Path(__file__).resolve().parents[3] / 'configs/paperfree-v19-training.json').read_text())
        qualify(row, cfg)
    else:
        row['qualified_complete'] = None
    return row
