"""Compare real contact/recovery alternatives from clone-verified reached states."""
import argparse
import hashlib
import json
from pathlib import Path
import pickle
import time

import modal
from mochi.navigation_tasks_v24.branches import evaluate
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_tasks_v24.policy import ACTIONS,observation

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);args=p.parse_args()
directory=root/'artifacts/continuation-v25'
source=json.loads((directory/(args.prefix+'.metadata.json')).read_text())
assert source['complete_sequence_success'],'Use physically completed, uninterrupted training prefixes'
target=directory/(args.prefix+'-components.json');assert not target.exists()
run=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id']
broker=modal.Function.from_name('mochi-continuation-v25','budget')
records=[]
for entry in source['snapshots']:
    domain,task=entry['domain'],entry['task']
    if domain=='navigation':continue
    assert all(entry['clone_check'][k] for k in ['qpos_exact','qvel_exact','control_exact'])
    raw=(directory/(args.prefix+'-states')/entry['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==entry['sha256']
    saved=pickle.loads(raw);w=restore(saved)
    obs=observation(w,domain,task)
    outcomes=[]
    for action in ACTIONS[domain]:
        ident=f'{args.prefix}-{domain}-{task}-{action}'
        broker.remote(run,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.05})
        started=time.perf_counter()
        row=evaluate(saved,domain,task,action)
        elapsed=time.perf_counter()-started
        broker.remote(run,ident+'-actual',{'simulation_cpu_hours':elapsed/3600-.05})
        row.update(id=ident,snapshot_sha256=entry['sha256'],provider='Local CPU',clone_check=entry['clone_check'])
        outcomes.append(row)
        record={'prefix':args.prefix,'layout_sha256':source['layout_sha256'],'records':records,'current_outcomes':outcomes,'status':'running'}
        target.write_text(json.dumps(record,indent=2)+'\n')
    valid=[r for r in outcomes if r['valid']]
    winner=min(valid,key=lambda r:r['rank'])['action'] if valid else None
    records.append({'domain':domain,'task':task,'observation':obs,'snapshot_sha256':entry['sha256'],
        'target':winner,'outcomes':outcomes})
    target.write_text(json.dumps({'prefix':args.prefix,'layout_sha256':source['layout_sha256'],'records':records,'status':'running'},indent=2)+'\n')
    print(json.dumps({'domain':domain,'task':task,'target':winner,'valid':[(r['action'],r['valid']) for r in outcomes]}),flush=True)
target.write_text(json.dumps({'prefix':args.prefix,'layout_sha256':source['layout_sha256'],'records':records,'status':'completed',
    'scope':'Component alternatives from actual clone-verified training states; not spliced complete-sequence trajectories.'},indent=2)+'\n')
