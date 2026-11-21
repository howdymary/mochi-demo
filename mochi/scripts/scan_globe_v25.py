"""Kinematic pose search on a planning copy of an owned recorded state."""
import hashlib
import json
import math
from pathlib import Path
import pickle
import time
import argparse
import mujoco

import numpy as np
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_tasks_v24.approaches import pose_corridor_clear, reachable_hand

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--shift',type=float,default=0.)
parser.add_argument('--id',default='globe-pose-scan')
args=parser.parse_args()
source = ROOT / 'artifacts/navigation-tasks-v24'
meta = json.loads((source / 'physical-r3-full.metadata.json').read_text())
entry = next(r for r in meta['snapshots'] if r['domain'] == 'navigation' and r['task'] == 'globe')
raw = (source / 'physical-r3-full-states' / entry['file']).read_bytes()
assert hashlib.sha256(raw).hexdigest() == entry['sha256']
w = restore(pickle.loads(raw))
if args.shift:
    fields=mujoco.mjtState.mjSTATE_FULLPHYSICS|mujoco.mjtState.mjSTATE_CTRL
    saved=np.empty(mujoco.mj_stateSize(w.m,fields))
    mujoco.mj_getState(w.m,w.d,saved,fields)
    for name in ['globe-base','globe']:
        w.m.body_pos[w.id('body',name),0]+=args.shift
    mujoco.mj_setConst(w.m,w.d)
    mujoco.mj_setState(w.m,w.d,saved,fields)
    mujoco.mj_forward(w.m,w.d)
original = w.d.qpos.copy()
centre = w.d.xpos[w.id('body', 'globe-base')].copy()
rows, counts = [], {'tested': 0, 'reachable': 0, 'clear_and_reachable': 0}
started = time.perf_counter()
for dx in [-.18, -.15, -.135, -.12, -.105, -.09, -.06, .06, .09, .12, .15]:
    for dy in [-.16, -.12, -.08, -.04, 0., .04, .08, .12]:
        for degrees in range(-180, 180, 30):
            goal = [float(centre[0]+dx), float(centre[1]+dy), math.radians(degrees)]
            if abs(goal[0]) > .57 or abs(goal[1]) > .37:
                continue
            counts['tested'] += 1
            error = reachable_hand(w, 'globe', goal)
            if error > .006:
                continue
            counts['reachable'] += 1
            if not pose_corridor_clear(w, goal, goal):
                continue
            counts['clear_and_reachable'] += 1
            rows.append({'goal': goal, 'offset': [dx, dy], 'heading_degrees': degrees,
                'ik_error_m': error, 'distance_from_recorded_root_m': math.dist(goal[:2], w.d.qpos[:2])})
assert np.array_equal(w.d.qpos, original), 'Planning must not move the physical root'
rows.sort(key=lambda r: (abs(r['heading_degrees']), r['distance_from_recorded_root_m'], r['ik_error_m']))
report = {'scope': 'Kinematic planning only, zero physical rollout or optimizer updates. Candidate poses still require actuator-driven validation.',
    'snapshot_sha256': entry['sha256'], 'recorded_root': original[:3].tolist(), 'globe_base': centre.tolist(),
    'counts': counts, 'candidates': rows, 'wall_seconds': time.perf_counter()-started}
target = ROOT / 'artifacts/continuation-v25'/(args.id+'.json')
assert not target.exists()
target.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({**counts, 'root': original[:3].tolist(), 'globe': centre.tolist(), 'best': rows[:12]}), flush=True)
