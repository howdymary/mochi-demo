"""Freeze measured task examples and launch the bounded task adapter campaign."""
import hashlib
import json
from pathlib import Path
import modal
from mochi.navigation_v23.layouts import fingerprint

root=Path(__file__).resolve().parents[1]
directory=root/'artifacts/continuation-v25'
config=root/'configs/continuation-v25/tasks'
study=json.loads((config/'study.json').read_text())
run=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id']
freeze=config/study['physical_freeze']
for name,expected in json.loads(freeze.read_text())['sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
training=[];development=[];provenance=[]
for prefix,output in [(p,training) for p in study['training_prefixes']]+[(study['development_prefix'],development)]:
    path=directory/(prefix+'-components.json');raw=path.read_bytes();data=json.loads(raw)
    assert data['status']=='completed'
    assert len(data['records'])==8
    for row in data['records']:
        assert row['target'] and any(o['action']==row['target'] and o['valid'] for o in row['outcomes'])
        output.append(dict(row,prefix=prefix,layout_sha256=data['layout_sha256']))
    provenance.append({'prefix':prefix,'sha256':hashlib.sha256(raw).hexdigest(),'role':'training' if output is training else 'development',
        'component_attempts':sum(len(r['outcomes']) for r in data['records'])})
splits=json.loads((config/'splits.json').read_text())
data={'final_opened':False,'training':training,'development':development,
    'engineering_sha256':hashlib.sha256(freeze.read_bytes()).hexdigest(),
    'final_set_sha256':fingerprint(json.loads((directory/'sealed/final_tasks.json').read_text())),
    'provenance':provenance,'study':study,'scope':'Two physically reached training prefixes, one separate development prefix. Component alternatives are not complete-sequence rollouts.'}
assert data['final_set_sha256']==splits['final']['sha256']
local=directory/'task-data.json';assert not local.exists()
local.write_text(json.dumps(data,indent=2)+'\n')
training_freeze={'sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
    [root/'scripts/train_tasks_v25.py',root/'scripts/probe_sequence_v25.py',root/'scripts/collect_task_components_v25.py',config/'study.json',freeze]},
    'data_sha256':hashlib.sha256(local.read_bytes()).hexdigest(),'final_opened':False,'task_optimizer_updates_before_freeze':0}
frozen=config/'training-source-freeze.json';assert not frozen.exists();frozen.write_text(json.dumps(training_freeze,indent=2)+'\n')
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
with volume.batch_upload() as batch:
    batch.put_file(local,'/'+run+'/task-data.json')
    batch.put_file(frozen,'/'+run+'/task-training-source-freeze.json')
launch=directory/'task-training-launch.json';assert not launch.exists()
call=modal.Function.from_name('mochi-task-control-v25','train').spawn()
receipt={'run_id':run,'call_id':call.object_id,'training_examples':len(training),'development_examples':len(development),
    'source_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),'updates_planned':16,'detached':True}
launch.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
