"""Check the higher swing reference from an actual completed training prefix."""
import gzip
import argparse
import hashlib
import json
from pathlib import Path
import pickle
import time
import modal

from mochi.balanced.sequence import PhysicalStop
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_v25.tasks import TaskWorld
from mochi.navigation_v25.task_approaches import task_pose,candidate_approach,transit
from mochi.navigation_tasks_v24 import policy

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
p=argparse.ArgumentParser();p.add_argument('--id',required=True);args=p.parse_args()
ident=args.id;target=directory/(ident+'.json.gz');assert not target.exists()
meta=json.loads((directory/'sequence-native-r3.metadata.json').read_text())
entry=next(x for x in meta['snapshots'] if x['domain']=='navigation' and x['task']=='globe')
raw=(directory/'sequence-native-r3-states'/entry['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['sha256']
w=restore(pickle.loads(raw),record=True);w.__class__=TaskWorld
run=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id'];broker=modal.Function.from_name('mochi-continuation-v25','budget')
broker.remote(run,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1});start=time.perf_counter()
begin=float(w.d.time);record={'scope':'Component branch, not a continuous sequence. Higher shared swing reference; zero optimizer updates.','snapshot_sha256':entry['sha256']}
try:
    goal=task_pose(w,'globe');approach=candidate_approach(w,goal)
    record['arrivals']=transit(w,approach['pose'],'globe',fine_goal=None if approach.get('direct_fine') else goal,fine_mode=approach['alignment_mode'],direct_fine=approach.get('direct_fine',False))
    record['task']=policy.execute(w,'globe','globe','G0')
    if record['task']['success']:record['recovery']=policy.execute(w,'recovery','globe','R4')
except PhysicalStop as error:record['failure']=str(error)
episode=w.episode();swings=[s['peak_minimum_sole_clearance_m'] for s in episode['flat_foot_clearance']['swings'] if s['start_t']>=begin and s['category'] in ['flat_transit','turning','fixture_clearance']]
import numpy as np
record.update(fall=w.fall,invalid_contact=w.invalid_contact,moving_swings=len(swings),median_moving_clearance_m=float(np.median(swings)) if swings else None)
target.write_bytes(gzip.compress(json.dumps({'record':record,'episode':episode},separators=(',',':')).encode(),mtime=0))
seconds=time.perf_counter()-start;broker.remote(run,ident+'-actual',{'simulation_cpu_hours':seconds/3600-.1})
(directory/(ident+'.metadata.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
