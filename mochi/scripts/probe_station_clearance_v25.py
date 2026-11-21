"""Budgeted matched branch from an actually reached task-navigation state."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import signal
from statistics import median
import time
import modal

from mochi.balanced.sequence import PhysicalStop
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_v25.task_approaches import candidate_approach, task_pose

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--id', required=True)
p.add_argument('--prefix', required=True)
p.add_argument('--task', choices=['drawer', 'laptop', 'globe'], required=True)
p.add_argument('--revision', choices=['r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9'], required=True)
p.add_argument('--action', choices=['direct', 'buffered'], default='direct')
p.add_argument('--torque-tau-ms',type=float,default=4.)
args = p.parse_args()
directory = root/'artifacts/continuation-v25'
target = directory/(args.id+'.json.gz')
assert not target.exists()
metadata = json.loads((directory/(args.prefix+'.metadata.json')).read_text())
entry = next(x for x in metadata['snapshots'] if x['domain']=='navigation' and x['task']==args.task)
raw = (directory/(args.prefix+'-states')/entry['file']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==entry['sha256']
assert all(entry['clone_check'][k] for k in ['qpos_exact','qvel_exact','control_exact'])
if args.revision=='r9':
    from mochi.navigation_v25.tasks_r9 import TaskWorld, transit
elif args.revision=='r8':
    from mochi.navigation_v25.tasks_r8 import TaskWorld, transit
elif args.revision=='r7':
    from mochi.navigation_v25.tasks_r7 import TaskWorld, transit
elif args.revision=='r6':
    from mochi.navigation_v25.tasks_r6 import TaskWorld, transit
elif args.revision=='r5':
    from mochi.navigation_v25.tasks_r5 import TaskWorld, transit
elif args.revision=='r4':
    from mochi.navigation_v25.tasks_r4 import TaskWorld, transit
elif args.revision=='r3':
    from mochi.navigation_v25.tasks_r3 import TaskWorld, transit
else:
    from mochi.navigation_v25.tasks import TaskWorld
    from mochi.navigation_v25.task_approaches import transit
w = restore(pickle.loads(raw), record=True)
w.__class__ = TaskWorld
w.station_torque_filter_tau_s=args.torque_tau_ms/1000.
broker = modal.Function.from_name('mochi-continuation-v25','budget')
run = 'mochi-nav25-20261121a'
broker.remote(run,args.id+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1})
started = time.perf_counter(); begin = float(w.d.time)
record = dict(id=args.id, revision=args.revision, task=args.task,
    snapshot_sha256=entry['sha256'], torque_filter_time_constant_s=args.torque_tau_ms/1000., scope='Component branch from a verified reached development state; not a continuous demonstration. Zero optimizer updates.')
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Station component ceiling')))
signal.setitimer(signal.ITIMER_REAL,360)
try:
    goal=task_pose(w,args.task); staging=candidate_approach(w,goal)
    def choose(*_):
        return {'action':args.action,'source':'Matched controller engineering probe; frozen action, no model inference.'}
    record['arrivals']=transit(w,staging['pose'],args.task,choose,
        fine_goal=None if staging.get('direct_fine') else goal,
        fine_mode=staging['alignment_mode'],direct_fine=staging.get('direct_fine',False))
    record['status']='completed'
except PhysicalStop as error:
    record.update(status='completed',physical_failure=str(error))
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
    elapsed=time.perf_counter()-started
    e=w.episode(); swings=[s['peak_minimum_sole_clearance_m'] for s in e['flat_foot_clearance']['swings']
        if s['start_t']>=begin and s['category'] in ['flat_transit','turning','fixture_clearance']]
    record.update(wall_seconds=elapsed, moving_swings=len(swings),
        moving_median_peak_m=median(swings) if swings else None,
        fall=w.fall,invalid_contact=w.invalid_contact,
        steps=e['steps']['attempts'],physical_seconds=float(w.d.time)-begin,native_smoothness=e['native_smoothness'])
    record['clearance_and_arrival_qualified']=bool(record.get('status')=='completed' and not record.get('physical_failure')
        and not w.fall and not w.invalid_contact and len(swings)>=2 and median(swings)>=.0045)
    native=e['native_smoothness']
    record['native_smoothness_qualified']=bool(native['sampled_acceleration_rms_rad_s2'] is not None
        and native['sampled_acceleration_rms_rad_s2']<=161.4
        and native['sampled_torque_change_rms_nm'] is not None
        and native['sampled_torque_change_rms_nm']<=.00371)
    record['qualified']=record['clearance_and_arrival_qualified'] and record['native_smoothness_qualified']
    record['gate_scope']='Component arrival, clearance, contact and native-smoothness limits. Full-sequence support and quality remain a separate mandatory gate.'
    payload=gzip.compress(json.dumps({'record':record,'episode':e},separators=(',',':')).encode(),mtime=0)
    target.write_bytes(payload);record['artifact_sha256']=hashlib.sha256(payload).hexdigest()
    (directory/(args.id+'.metadata.json')).write_text(json.dumps(record,indent=2)+'\n')
    broker.remote(run,args.id+'-actual',{'simulation_cpu_hours':elapsed/3600-.1})
    print(json.dumps({k:v for k,v in record.items() if k!='arrivals'}),flush=True)
