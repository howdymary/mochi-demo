"""A bounded physical component probe using the new global study budget."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickle
import signal
import time

import modal
from mochi.balanced.sequence import PhysicalStop
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_tasks_v24.departure import clear_globe_turn
from mochi.navigation_tasks_v24.approaches import task_pose, transit, pose_corridor_clear
from mochi.navigation_tasks_v24 import policy

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--id', required=True)
parser.add_argument('--distance', type=float, default=.04)
parser.add_argument('--dx', type=float, default=-.12)
parser.add_argument('--dy', type=float, default=-.04)
parser.add_argument('--yaw', type=float, default=90.)
parser.add_argument('--tuck', action='store_true')
parser.add_argument('--warm', action='store_true')
parser.add_argument('--globe-shift', type=float, default=0.)
parser.add_argument('--native-arms', action='store_true')
parser.add_argument('--clearance-east', type=float, default=0.)
args = parser.parse_args()
assert args.id.replace('-', '').isalnum()
directory = ROOT / 'artifacts/continuation-v25'
target = directory / (args.id + '.json.gz')
assert not target.exists()
run = json.loads((ROOT / 'configs/continuation-v25/protocol.json').read_text())['id']
broker = modal.Function.from_name('mochi-continuation-v25', 'budget')
broker.remote(run, args.id+'-reserve', {'physical_rollouts': 1, 'simulation_cpu_hours': 300/3600})
started = time.perf_counter()
record = {'id': args.id, 'scope': 'Actuator-driven component branch from a measured training prefix; not an uninterrupted demonstration.',
    'parameters': vars(args), 'status': 'running', 'source_sha256': {
        str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__),ROOT/'src/mochi/navigation_v25/globe.py']}}
(directory / (args.id+'.metadata.json')).write_text(json.dumps(record, indent=2)+'\n')
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Globe probe wall ceiling')))
signal.setitimer(signal.ITIMER_REAL, 300)
try:
    source = ROOT / 'artifacts/navigation-tasks-v24'
    meta = json.loads((source / 'physical-r3-full.metadata.json').read_text())
    entry = next(r for r in meta['snapshots'] if r['domain'] == 'navigation' and r['task'] == 'globe')
    raw = (source/'physical-r3-full-states'/entry['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    w = restore(pickle.loads(raw), record=True)
    if args.globe_shift:
        # A separately labeled component scene change at branch initialization.
        # Full sequences must apply this offset in their scene at reset.
        import mujoco
        import numpy as np
        fields=mujoco.mjtState.mjSTATE_FULLPHYSICS|mujoco.mjtState.mjSTATE_CTRL
        state=np.empty(mujoco.mj_stateSize(w.m,fields))
        mujoco.mj_getState(w.m,w.d,state,fields)
        for name in ['globe-base','globe']:
            w.m.body_pos[w.id('body',name),0]+=args.globe_shift
        mujoco.mj_setConst(w.m,w.d)
        mujoco.mj_setState(w.m,w.d,state,fields)
        mujoco.mj_forward(w.m,w.d)
        w.frames=[];w.capture()
        record['environment_engineering']='Globe translated at component initialization; not evidence of uninterrupted execution or learned improvement.'
    if args.native_arms:
        from mochi.balanced.onnx_walk import HubWalker
        from mochi.navigation_tasks_v24 import navigation,approaches
        navigation.HubWalker=HubWalker
        approaches.NavigationWalker=HubWalker
    w.warm_resume=args.warm
    record['snapshot_sha256'] = entry['sha256']
    if args.tuck:
        from mochi.navigation_v25.globe import tuck_for_globe
        record['arm_clearance'] = tuck_for_globe(w)
    if args.distance>0:
        record['retreat'] = clear_globe_turn(w, args.distance)
    else:
        record['retreat'] = {'method':'No contact-walker retreat; bounded native-gait station alignment.'}
    if args.clearance_east:
        clearance=[float(w.d.qpos[0]+args.clearance_east),float(w.d.qpos[1]),w.yaw()]
        start=[*w.d.qpos[:2].tolist(),w.yaw()]
        if not pose_corridor_clear(w,start,clearance):
            raise PhysicalStop('laptop-departure-corridor-not-clear')
        record['departure']=transit(w,clearance,'globe-departure',direct_fine=True,fine_mode='fixed_heading')
    p = w.d.xpos[w.id('body', 'globe-base')]
    w.task_poses['globe'] = [float(p[0]+args.dx), float(p[1]+args.dy), math.radians(args.yaw)]
    goal = task_pose(w, 'globe')
    start = [*w.d.qpos[:2].tolist(), w.yaw()]
    if not pose_corridor_clear(w, start, goal):
        raise PhysicalStop('oriented-globe-corridor-not-clear')
    record['arrival'] = transit(w, goal, 'globe', direct_fine=True, fine_mode='fixed_heading')
    record['result'] = policy.execute(w, 'globe', 'globe', 'G0')
    if record['result']['success']:
        record['recovery'] = policy.execute(w, 'recovery', 'globe', 'R4')
    record['status'] = 'completed'
except PhysicalStop as error:
    record.update(status='completed', physical_failure=str(error))
except BaseException as error:
    record.update(status='incomplete', error_type=type(error).__name__)
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    elapsed = time.perf_counter()-started
    if 'w' in locals():
        episode = w.episode()
        payload = gzip.compress(json.dumps({'episode': episode, 'record': record}, separators=(',', ':')).encode(), mtime=0)
        target.write_bytes(payload)
        record.update(artifact_sha256=hashlib.sha256(payload).hexdigest(), fall=w.fall,
            invalid_contact=w.invalid_contact, contact_failures=episode['contact_failures'])
        from mochi.balanced.onnx_walk import HoldWalker
        if isinstance(w.walker,HoldWalker):
            from mochi.smooth_v16.world import state
            saved=pickle.dumps(state(w,include_history=False),protocol=pickle.HIGHEST_PROTOCOL)
            (directory/(args.id+'-final.pickle')).write_bytes(saved)
            record['final_state_sha256']=hashlib.sha256(saved).hexdigest()
        else:
            record['final_state_export']='Unsupported walker state; complete numerical episode retained instead.'
    record['wall_seconds'] = elapsed
    broker.remote(run, args.id+'-actual', {'simulation_cpu_hours': elapsed/3600-300/3600})
    (directory / (args.id+'.metadata.json')).write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ['retreat','arrival']}), flush=True)
