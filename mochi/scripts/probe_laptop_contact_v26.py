"""Controlled development counterfactual; fixture friction changes at branch reset.

This is not a continuous full-sequence result and not an opened-final label.
The robot begins at an exact measured development state. No robot pose is edited.
"""
import argparse
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import signal
import time
import modal
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_v25.tasks import TaskWorld
from mochi.contact_v18.policy import PRESSES
from mochi.navigation_v25.laptop_contact_v26 import adaptive_laptop
from mochi.balanced.sequence import PhysicalStop

root=Path(__file__).resolve().parents[1];d=root/'artifacts/continuation-v25'
p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--force',type=float,default=.72)
p.add_argument('--backoff',type=float,default=.74);p.add_argument('--friction',type=float,default=.075)
p.add_argument('--keep-friction',action='store_true');p.add_argument('--original-controller',action='store_true')
p.add_argument('--reapproach',action='store_true');p.add_argument('--pulse-degrees',type=float,default=68.);p.add_argument('--pulse-delay',type=float,default=1.2)
p.add_argument('--horizon',type=float,default=32.);p.add_argument('--pulse-force',type=float,default=.60)
p.add_argument('--pulse-ramp',type=float,default=0.)
p.add_argument('--hinge-projection',action='store_true');p.add_argument('--project-damping',action='store_true')
args=p.parse_args();assert .4<=args.force<=.74 and args.force<=args.backoff<=.76
target=d/(args.id+'.json.gz');assert not target.exists()
meta=json.loads((d/'sequence-task-development-r7.metadata.json').read_text())
entry=next(x for x in meta['snapshots'] if x['domain']=='laptop' and x['task']=='laptop')
raw=(d/'sequence-task-development-r7-states'/entry['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['sha256']
w=restore(pickle.loads(raw),record=True);w.__class__=TaskWorld
old=float(w.m.dof_frictionloss[w.v['laptop']]);args.friction=old if args.keep_friction else args.friction;w.m.dof_frictionloss[w.v['laptop']]=args.friction;w.s['laptop_friction']=args.friction
w.laptop_hinge_projection=args.hinge_projection;w.laptop_project_damping=args.project_damping;w.laptop_pulse_ramp_s=args.pulse_ramp;w.laptop_pulse_force_n=args.pulse_force;w.laptop_reapproach_enabled=args.reapproach;w.laptop_pulse_degrees=args.pulse_degrees;w.laptop_pulse_delay_s=args.pulse_delay;w.laptop_force_backoff_n=args.backoff;w.contact_closing_speed=.4;w.efficiency_segment='manipulation'
broker=modal.Function.from_name('mochi-continuation-v25','budget');run='mochi-nav25-20261121a'
broker.remote(run,args.id+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1})
started=time.perf_counter();record={'id':args.id,'parameters':vars(args),'snapshot_sha256':entry['sha256'],
    'reset_intervention':{'hinge_friction_Nm_before':old,'hinge_friction_Nm_after':args.friction},
    'scope':'Development-only counterfactual component. Measured robot state; fixture-friction intervention at reset. No robot teleport or invented trajectory. Not a complete sequence.'}
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Contact probe wall ceiling')))
signal.setitimer(signal.ITIMER_REAL,360)
try:
    profile=replace(PRESSES['P5'],code='P7' if args.force>.65 else 'P5',force=args.force)
    if args.original_controller:
        from mochi.navigation_tasks_v24 import policy
        assert args.force==.65 and args.backoff==.65
        record['result']=policy.execute(w,'laptop','laptop','P5')
    else:record['result']=adaptive_laptop(w,profile,args.horizon)
    record['status']='completed'
except PhysicalStop as error:record.update(status='completed',physical_failure=str(error))
finally:
    signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.perf_counter()-started
    episode=w.episode();payload=gzip.compress(json.dumps({'record':record,'episode':episode},separators=(',',':')).encode(),mtime=0)
    target.write_bytes(payload);record.update(wall_seconds=elapsed,artifact_sha256=hashlib.sha256(payload).hexdigest(),
        fall=w.fall,invalid_contact=w.invalid_contact)
    (d/(args.id+'.metadata.json')).write_text(json.dumps(record,indent=2)+'\n')
    broker.remote(run,args.id+'-actual',{'simulation_cpu_hours':elapsed/3600-.1})
    result=record.get('result',{})
    print(json.dumps({'id':args.id,'success':result.get('success'),'angle':result.get('value'),
        'max_force_n':result.get('max_force_n'),'abort':result.get('abort'),'failure':record.get('physical_failure'),
        'duration_s':result.get('duration'),'fall':w.fall,'invalid_contact':w.invalid_contact}),flush=True)
