"""A budgeted uninterrupted four-task attempt with explicit scene revision."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import platform
import signal
import time

import modal
from mochi.navigation_v23.layouts import fingerprint

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--id',required=True)
p.add_argument('--seed',type=int,default=231000)
p.add_argument('--layout',type=Path)
p.add_argument('--capture',action='store_true')
p.add_argument('--policy-config',type=Path)
p.add_argument('--engineering-revision',choices=['r2','r3','r5','contact-v26','contact-v26r2','contact-v26r3','contact-v26r4'],default='r2')
args=p.parse_args()
if args.engineering_revision=='contact-v26r4':
    from mochi.navigation_v25.tasks_contact_v26r4 import run
elif args.engineering_revision=='contact-v26r3':
    from mochi.navigation_v25.tasks_contact_v26r3 import run
elif args.engineering_revision=='contact-v26r2':
    from mochi.navigation_v25.tasks_contact_v26r2 import run
elif args.engineering_revision=='contact-v26':
    from mochi.navigation_v25.tasks_contact_v26 import run
elif args.engineering_revision=='r5':
    from mochi.navigation_v25.tasks_r5 import run
elif args.engineering_revision=='r3':
    from mochi.navigation_v25.tasks_r3 import run
else:
    from mochi.navigation_v25.tasks import run
if args.policy_config:
    freeze_path=root/f'configs/continuation-v25/tasks/physical-freeze-{args.engineering_revision}.json'
    if args.engineering_revision=='contact-v26':freeze_path=root/'configs/laptop-contact-v26/source-freeze.json'
    if args.engineering_revision=='contact-v26r2':freeze_path=root/'configs/laptop-contact-v26/source-freeze-r2.json'
    if args.engineering_revision=='contact-v26r3':freeze_path=root/'configs/laptop-contact-v26/source-freeze-r3.json'
    if args.engineering_revision=='contact-v26r4':freeze_path=root/'configs/laptop-contact-v26/source-freeze-r4.json'
    freeze=json.loads(freeze_path.read_text())
    for name,expected in freeze['sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
directory=root/'artifacts/continuation-v25'
out=directory/(args.id+'.json.gz')
assert not out.exists()
if args.layout:
    layout=json.loads(args.layout.read_text())
    if isinstance(layout,list):
        assert len(layout)==1
        layout=layout[0]
else:
    previous=json.loads(gzip.decompress((root/'artifacts/navigation-tasks-v24/physical-r3-full.json.gz').read_bytes()))
    layout=copy.deepcopy(previous['layout'])
    for name in ['globe-base','globe']:
        offsets=layout['scene'].setdefault('station_offsets',{})
        offsets[name]=( __import__('numpy').asarray(offsets.get(name,[0.,0.,0.]))+[.05,0.,0.]).tolist()
    layout['scene']['version']='navigation-tasks-v25-globe-workspace-r1'
    layout['scope']='Development scene engineering: whole globe assembly 5 cm east at reset; exact same task and physical quality verifiers.'
    layout['layout_sha256']=fingerprint({'scene':layout['scene'],'goal':layout['goal']})
    (directory/(args.id+'-layout.json')).write_text(json.dumps(layout,indent=2)+'\n')
broker=modal.Function.from_name('mochi-continuation-v25','budget')
rid=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id']
broker.remote(rid,args.id+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.3})
started=time.perf_counter()
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Sequence wall limit')))
signal.setitimer(signal.ITIMER_REAL,1080)
snapshots=[]
decisions=[]
settings=json.loads(args.policy_config.read_text()) if args.policy_config else None
def choose(domain,task,observed,prompt):
    ident=f'{args.id}-{len(decisions)}-{domain}-{task}'
    if domain=='navigation' and settings['navigation']['mode']=='fixed':
        preferred=settings['navigation']['action']
        order=list(dict.fromkeys([preferred,'buffered','wide_fast','direct']))
        action=next(a for a in order if observed['options'][a]['feasible'])
        picked={'action':action,'source':'Training-selected fixed navigation profile with shared geometric feasibility mask',
            'preferred_action':preferred,'geometric_mask_changed_choice':preferred!=action}
    else:
        key='navigation' if domain=='navigation' else 'task'
        kind='compact_navigation' if key=='navigation' and settings[key].get('representation')=='compact' else key
        picked=modal.Function.from_name('mochi-task-control-v25','choose').remote(kind,settings[key]['update'],observed,ident)
    decisions.append({'domain':domain,'task':task,'selection':picked})
    return picked
def capture(w,domain,task):
    from mochi.navigation_tasks_v24.snapshot import capture_and_verify
    state=capture_and_verify(w)
    folder=directory/(args.id+'-states');folder.mkdir(exist_ok=True)
    name=f'{len(snapshots)}-{domain}-{task}.pickle'
    b=pickle.dumps(state,protocol=pickle.HIGHEST_PROTOCOL);(folder/name).write_bytes(b)
    snapshots.append({'domain':domain,'task':task,'file':name,'sha256':hashlib.sha256(b).hexdigest(),'t':float(w.d.time),'clone_check':state['clone_check']})
try:
    row=run(layout,args.seed,choose=choose if settings else None,capture=capture if args.capture else None)
    b=gzip.compress(json.dumps(row,separators=(',',':')).encode(),compresslevel=1,mtime=0)
    out.write_bytes(b)
    episode=row['episode']
    report={'id':args.id,'status':'completed','failure':row['failure'],'qualified_complete':row['qualified_complete'],
        'complete_sequence_success':row['complete_sequence_success'],'tasks':{k:v['success'] for k,v in episode['results'].items()},
        'steps':episode['steps']['attempts'],'physical_seconds':episode['duration'],'fall':episode['fall'],
        'invalid_contact':episode['invalid_contact'],'contacts':episode['contact_failures'],
        'snapshots':snapshots,'sha256':hashlib.sha256(b).hexdigest(),'layout_sha256':layout['layout_sha256'],
        'source_sha256':hashlib.sha256((root/'src/mochi/navigation_v25/tasks.py').read_bytes()).hexdigest(),'evaluation_partition':layout.get('partition'),
        'engineering_revision':args.engineering_revision,
        'source_freeze_sha256':hashlib.sha256(freeze_path.read_bytes()).hexdigest() if args.policy_config else None,
        'receipt':{'provider':'local','architecture':platform.machine(),'physical_rollouts':1,'cpu_threads':1},
        'scope':row['scope'],'policy_settings':settings,'checkpoint_decisions':decisions}
except BaseException as error:
    report={'id':args.id,'status':'incomplete','error_type':type(error).__name__,'error':str(error)[:160],'snapshots':snapshots,'scope':'Interrupted software attempt; no complete-sequence outcome inferred.'}
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
    seconds=time.perf_counter()-started
    broker.remote(rid,args.id+'-actual',{'simulation_cpu_hours':seconds/3600-.3})
    if 'report' in locals():
        report['wall_seconds']=seconds
        (directory/(args.id+'.metadata.json')).write_text(json.dumps(report,indent=2)+'\n')
if 'report' in locals():
    report['wall_seconds']=seconds
    (directory/(args.id+'.metadata.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='snapshots'}),flush=True)
