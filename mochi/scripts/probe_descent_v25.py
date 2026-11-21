"""Matched descent tuning after an observed fall on a training physics seed."""
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import time

import modal
from mochi.balanced.sequence import PhysicalStop
from mochi.balanced.onnx_walk import HoldWalker
from mochi.navigation_tasks_v24.snapshot import restore,capture_and_verify
from mochi.navigation_tasks_v24 import policy
from mochi.navigation_v25.tasks import TaskWorld
from mochi.smooth_v16.terrain import clear_and_turn,forward_descent
from mochi.smooth_v16.policy import WALKS
from mochi.terrain_v12.legs import BASE
from mochi.smooth_v16.objective import branch_metrics

root=Path(__file__).resolve().parents[1];folder=root/'artifacts/continuation-v25/descent';folder.mkdir(exist_ok=True)
run=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id']
broker=modal.Function.from_name('mochi-continuation-v25','budget')
records=[]


def begin(ident):
    assert not (folder/(ident+'.json.gz')).exists()
    broker.remote(run,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.15})
    return time.perf_counter()


def finish(ident,w,record,started):
    record.update(fall=w.fall,invalid_contact=w.invalid_contact,wall_seconds=time.perf_counter()-started,
        scope='Actuator-driven training-state component experiment. No new learned weights or continuous four-task outcome.')
    raw=gzip.compress(json.dumps({'record':record,'episode':w.episode()},separators=(',',':')).encode(),compresslevel=1,mtime=0)
    (folder/(ident+'.json.gz')).write_bytes(raw)
    broker.remote(run,ident+'-actual',{'simulation_cpu_hours':record['wall_seconds']/3600-.15})
    records.append(record);(folder/'results.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(record),flush=True)


for prefix in ['sequence-clearance-r4','sequence-train-firm-r5']:
    meta=json.loads((folder.parent/(prefix+'.metadata.json')).read_text())
    entry=next(x for x in meta['snapshots'] if x['domain']=='recovery' and x['task']=='alarm')
    raw=(folder.parent/(prefix+'-states')/entry['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['sha256']
    w=restore(pickle.loads(raw),record=True);w.__class__=TaskWorld
    ident=prefix+'-supported-turn';started=begin(ident);result={'id':ident,'prefix':prefix,'source_sha256':entry['sha256']}
    try:
        result['recovery']=policy.execute(w,'recovery','alarm','R4')
        parameters={**BASE,**{k:v for k,v in WALKS['W5'].items() if k!='flat_speed'}}
        result['arrivals']=clear_and_turn(w,parameters)
        saved=capture_and_verify(w)
        raw=pickle.dumps(saved,protocol=pickle.HIGHEST_PROTOCOL);(folder/(ident+'.pickle')).write_bytes(raw)
        result['state_sha256']=hashlib.sha256(raw).hexdigest()
    except PhysicalStop as error:result['failure']=str(error)
    finish(ident,w,result,started)
    if 'failure' in result:continue
    for profile in ['W5','W0','W1']:
        w=restore(saved,record=True);w.__class__=TaskWorld
        ident=prefix+'-descent-'+profile;started=begin(ident);start=float(w.d.time)
        measurement_start=len(w.measurements)
        record={'id':ident,'prefix':prefix,'profile':profile,'start_state_sha256':result['state_sha256']}
        try:
            parameters={**BASE,**{k:v for k,v in WALKS[profile].items() if k!='flat_speed'}}
            record['arrivals']=forward_descent(w,parameters)
            record['success']=all(x['success'] for x in record['arrivals'])
        except PhysicalStop as error:record.update(success=False,failure=str(error))
        record['physical_seconds']=float(w.d.time)-start
        record['metrics']=branch_metrics(w.measurements[measurement_start:])
        record['steps']=w.step_counter.summary(since=start)['attempts']
        record['qualified']=bool(record['success'] and not w.fall and not w.invalid_contact and record['metrics']['roll_rms_deg']<=2 and record['metrics']['roll_peak_deg']<=12)
        finish(ident,w,record,started)
