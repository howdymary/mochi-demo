"""Finish collection, launch bounded training, overlap frozen final cohorts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import modal

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
run='mochi-nav25-20261121a';volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
launch=directory/'compact-training-launch.json';assert not launch.exists()
(directory/'compact-driver.json').write_text(json.dumps({'pid':os.getpid(),'scope':'Owned compact study coordinator; no sub-agent.'},indent=2)+'\n')
log=directory/'compact-local-collection.jsonl'
print('Waiting for all 32 additional physical training requests to finish uploading.',flush=True)
while not log.exists() or len(log.read_text().splitlines())<32:time.sleep(5)
freeze=json.loads((root/'configs/continuation-v25/compact/source-freeze.json').read_text())
for name,h in freeze['sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h,name
command=[str(root/'.venv/bin/modal'),'run',str(root/'scripts/prepare_compact_study_v25.py')]
assert subprocess.run(command).returncode==0
data=json.loads((directory/'compact-data-freeze.json').read_text())
assert data['exact_reuse_pairs']==2 and data['development_oracle_upper_bound']['win'] and not data['final_opened']
assert all(data['targets'].get(a,0)>1 for a in ['direct','buffered'])
with volume.batch_upload() as batch:
    batch.put_file(root/'configs/continuation-v25/compact/source-freeze.json','/'+run+'/compact/source-freeze.json')
    batch.put_file(root/'configs/continuation-v25/compact/protocol.json','/'+run+'/compact/protocol.json')
call=modal.Function.from_name('mochi-navigation-v25-compact-training','train').spawn()
receipt={'call_id':call.object_id,'new_optimizer_updates_planned':16,'global_navigation_parent_update':32,
    'data_sha256':data['data_sha256'],'final_opened':False,'detached':True}
launch.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
task=None;last=None
while True:
    try:report=json.loads(b''.join(volume.read_file(run+'/compact/navigation-training.json')))
    except (modal.exception.NotFoundError,FileNotFoundError):time.sleep(5);continue
    state=(report['status'],report['phase'],report['optimizer_updates_completed'])
    if state!=last:print(json.dumps({'compact_status':state,'task_final_started':task is not None}),flush=True);last=state
    if report['status']=='incomplete':raise RuntimeError('Compact training needs inspection; saved states and outputs are preserved')
    if task is None and ((report.get('selected_checkpoint') and report['final_opened']) or report['status']=='development_goal_unmet'):
        print('Frozen navigation selection ready; starting uninterrupted final task pairs concurrently.',flush=True)
        task=subprocess.Popen([sys.executable,str(root/'scripts/evaluate_task_checkpoints_v25.py'),'--phase','final'])
    if task is not None and task.poll() is not None:
        assert task.returncode==0,'Inspect retained final-task logs and incomplete attempts'
        if report['status'] in ['completed','development_goal_unmet']:break
    time.sleep(10)
print(json.dumps({'compact_navigation_status':report['status'],'task_final_completed':True}),flush=True)
