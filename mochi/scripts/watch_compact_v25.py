"""Resume orchestration of the already-spawned study without retraining."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import modal

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
receipt=json.loads((directory/'compact-training-launch.json').read_text())
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts');run='mochi-nav25-20261121a'
(directory/'compact-watch.json').write_text(json.dumps({'pid':os.getpid(),'call_id':receipt['call_id'],'optimizer_updates_repeated':0},indent=2)+'\n')
task=None;last=None
while True:
    try:report=json.loads(b''.join(volume.read_file(run+'/compact/navigation-training.json')))
    except (modal.exception.NotFoundError,FileNotFoundError):time.sleep(5);continue
    state=(report['status'],report['phase'],report['optimizer_updates_completed'])
    if state!=last:print(json.dumps({'compact_status':state,'task_final_started':task is not None}),flush=True);last=state
    if report['status']=='incomplete':raise RuntimeError('Inspect the preserved incomplete training report; no optimizer update is repeated')
    if task is None and ((report.get('selected_checkpoint') and report['final_opened']) or report['status']=='development_goal_unmet'):
        print('Starting final task comparisons after navigation selection is frozen.',flush=True)
        task=subprocess.Popen([sys.executable,str(root/'scripts/evaluate_task_checkpoints_v25.py'),'--phase','final'])
    if task is not None and task.poll() is not None:
        assert task.returncode==0,'Inspect retained final-task logs'
        if report['status'] in ['completed','development_goal_unmet']:break
    time.sleep(10)
print(json.dumps({'navigation_status':report['status'],'task_final_completed':True}),flush=True)
