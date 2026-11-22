"""Three prospective single-model attempts; no new model-weight claim."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from mochi.navigation_v23.layouts import fingerprint

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
config=root/'configs/laptop-contact-v26'
protocol=json.loads((config/'heading-validation-protocol.json').read_text())
amendment=json.loads((config/'heading-validation-r4-amendment.json').read_text())
assert amendment['final_set_sha256']==protocol['final_set_sha256']
freeze=config/'source-freeze-r4.json';source_sha=hashlib.sha256(freeze.read_bytes()).hexdigest()
for name,expected in json.loads(freeze.read_text())['sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
development=json.loads((directory/'contact26r4-dev-selected.metadata.json').read_text())
assert development['status']=='completed' and development['qualified_complete'] and development['source_freeze_sha256']==source_sha,'Keep validation sealed until the R4 development run qualifies'
sealed=directory/'contact-v26/sealed-heading-validation.json';layouts=json.loads(sealed.read_text())
assert len(layouts)==3 and fingerprint(layouts)==protocol['final_set_sha256']
marker=directory/'heading26-final-opened.json'
assert not marker.exists(),'Preserve the opened validation cohort'
marker.write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'final_set_sha256':fingerprint(layouts),
    'source_freeze_sha256':source_sha,'development_sha256':development['sha256'],
    'scope':'Prospective product validation of shared controller engineering with frozen navigation-48/task-8 weights. No parent-model comparison, no new optimizer update.'},indent=2)+'\n')
settings={'navigation':{'mode':'tinker','representation':'compact','update':48},'task':{'update':8}}
jobs=[]
for index,(layout,seed) in enumerate(zip(layouts,protocol['physics_seed_by_layout'],strict=True)):
    ident=f'heading26-final-{index}-{seed}-selected'
    path=directory/(ident+'-layout.json');assert not path.exists();path.write_text(json.dumps(layout,indent=2)+'\n')
    policy=directory/(ident+'-policy.json');assert not policy.exists();policy.write_text(json.dumps(settings,indent=2)+'\n')
    jobs.append((ident,path,policy,seed))

def attempt(job):
    ident,layout,policy,seed=job
    command=[sys.executable,str(root/'scripts/probe_sequence_v25.py'),'--id',ident,'--seed',str(seed),
        '--layout',str(layout),'--policy-config',str(policy),'--engineering-revision','contact-v26r4']
    with (directory/(ident+'.log')).open('w') as log:
        completed=subprocess.run(command,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT)
    assert completed.returncode==0,(ident,'Incomplete attempt retained')
    result=json.loads((directory/(ident+'.metadata.json')).read_text())
    assert result['status']=='completed' and result['source_freeze_sha256']==source_sha
    print(json.dumps({k:result[k] for k in ['id','qualified_complete','failure','steps','physical_seconds']}),flush=True)
    return result

with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(attempt,jobs))
output=directory/'heading26-product-final.json';assert not output.exists()
output.write_text(json.dumps({'results':results,'n':3,'qualified':sum(r['qualified_complete'] for r in results),
    'final_set_sha256':fingerprint(layouts),'source_freeze_sha256':source_sha,'optimizer_updates_added':0,
    'scope':'Three new arrangements, one new physics seed each, one uninterrupted selected-model run from reset per arrangement. Failures retained. Product validation of controller engineering; does not establish a model-weight or memory benefit.'},indent=2)+'\n')
