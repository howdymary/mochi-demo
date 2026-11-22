"""Geometry-only diagnosis from measured body transforms. Executes no physics."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import mujoco
import numpy as np
from mochi.navigation_v25.tasks import TaskWorld
from mochi.navigation_v25.task_approaches import candidate_approach, pose_corridor_clear
from mochi.navigation_v25.planner import plan
from mochi.balanced.sequence import PhysicalStop

root = Path(__file__).resolve().parents[1]
source = root / 'artifacts/continuation-v25/contact26-final-0-254000-selected.json.gz'
raw = source.read_bytes()
row = json.loads(gzip.decompress(raw))
episode = row['episode']
frame = episode['trajectory']['frames'][-1]
names = episode['trajectory']['body_names']
indices = {name: i for i, name in enumerate(names)}
w = TaskWorld(row['layout'], row['seed'], False)
def matrix(q):
    out = np.empty(9)
    mujoco.mju_quat2Mat(out, np.asarray(q))
    return out.reshape(3, 3)
pelvis = indices['pelvis']
w.d.qpos[:3] = frame['positions'][pelvis]
w.d.qpos[3:7] = frame['quaternions'][pelvis]
for joint in range(w.m.njnt):
    body = int(w.m.jnt_bodyid[joint])
    if body not in w.robot_bodies or w.m.jnt_type[joint] != mujoco.mjtJoint.mjJNT_HINGE:
        continue
    name = mujoco.mj_id2name(w.m, mujoco.mjtObj.mjOBJ_BODY, body)
    parent = int(w.m.body_parentid[body])
    parent_name = mujoco.mj_id2name(w.m, mujoco.mjtObj.mjOBJ_BODY, parent)
    relative = matrix(w.m.body_quat[body]).T @ matrix(frame['quaternions'][indices[parent_name]]).T @ matrix(frame['quaternions'][indices[name]])
    skew = np.array([relative[2, 1]-relative[1, 2], relative[0, 2]-relative[2, 0], relative[1, 0]-relative[0, 1]]) / 2
    w.d.qpos[w.m.jnt_qposadr[joint]] = math.atan2(float(w.m.jnt_axis[joint] @ skew), float((np.trace(relative)-1)/2))
mujoco.mj_forward(w.m, w.d)
error = max(float(np.max(np.abs(w.d.xpos[body]-frame['positions'][indices[mujoco.mj_id2name(w.m, mujoco.mjtObj.mjOBJ_BODY, body)]]))) for body in w.robot_bodies)
assert error < 5e-6, ('Recorded FK reconstruction mismatch', error)
goal = w.station_goal('drawer')
try:
    previous = candidate_approach(w, goal)
except PhysicalStop as failure:
    previous = {'failure': str(failure)}
forward = np.array([math.cos(goal[2]), math.sin(goal[2])])
lateral = np.array([-forward[1], forward[0]])
found = []
for back in [.015, .020, .025, .030, .035]:
    for side in [0., .015, -.015, .03, -.03]:
        point = np.asarray(goal[:2])-back*forward+side*lateral
        staging = [*point.tolist(), goal[2]]
        paths = [plan(w.d.qpos[:2], staging, w.obstacles(), w.envelope(), code) for code in ['planner','buffered','direct']]
        feasible = next((p for p in paths if p['feasible']), None)
        if not feasible:
            continue
        for mode in ['turn_at_goal', 'fixed_heading']:
            if pose_corridor_clear(w, staging, goal, mode=='turn_at_goal'):
                found.append({'back_m':back,'lateral_m':side,'pose':staging,'mode':mode,'path':feasible})
                break
result = {'source_sha256':hashlib.sha256(raw).hexdigest(),'recorded_t':frame['t'],
    'maximum_robot_fk_error_m':error,'goal':goal,'original':previous,'additional_candidates':found,
    'physics_steps':0,'scope':'Planning-only reconstruction from a sampled measured pose. No physical trajectory is generated or modified. Additional staging candidates retain the original collision and foot-swing checks. This diagnoses an opened cohort for a subsequent study; it never changes the frozen final comparison.'}
target = root / 'evidence/continuation-v25/approach-geometry-diagnosis.json'
assert not target.exists()
target.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'previous':previous,'additional_feasible_candidates':len(found),'fk_error_m':error,'physics_steps':0}))
