"""Expose all four continuous task checkpoints after development selection."""
import gzip
import hashlib
import json
from pathlib import Path
import modal
from mochi.smooth_v16.public import rounded

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
target=root/'web/desk/continuation-v25/manifest.json';manifest=json.loads(target.read_text())
case=next(c for c in manifest['cases'] if c['id']=='task-weight-development')
assert 'u4' not in case['runs']
case['runs']['u4']=case['runs']['selected']
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts');run=manifest['run_id']
report=json.loads(b''.join(volume.read_file(run+'/task-training.json')))
selection=json.loads((directory/'task-selection-freeze.json').read_text());assert selection['selected_update']==8
uploads=[]
for u in [8,16]:
    ident='task-dev-u'+str(u);metadata=json.loads((directory/(ident+'.metadata.json')).read_text())
    raw=(directory/(ident+'.json.gz')).read_bytes();assert hashlib.sha256(raw).hexdigest()==metadata['sha256']
    episode=json.loads(gzip.decompress(raw))['episode']
    public={k:v for k,v in episode.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
    public['balance_measurements']=[{k:v for k,v in r.items() if k in ['t','phase','roll_rad','loads_n','step_category']} for r in episode['balance_measurements']]
    public['model_decisions']=episode['decisions']
    packed=gzip.compress(json.dumps(rounded(public),separators=(',',':')).encode(),mtime=0)
    name='progress-'+ident+'.json.gz';path=directory/name;assert not path.exists();path.write_bytes(packed)
    destination=run+'/public/'+name;uploads.append((path,'/'+destination));sha=hashlib.sha256(packed).hexdigest()
    manifest['recordings'][name]={'path':destination,'sha256':sha,'bytes':len(packed)}
    cp=next(c for c in report['checkpoints'] if c['update']==u)
    label=('Development-selected task weights' if u==8 else 'Task weights')+' · update '+str(u)
    case['runs']['selected' if u==8 else 'u16']={'file':name,'label':label,'sha256':sha,
        'row':{'kind':'sequence','qualified_complete':metadata['qualified_complete'],'steps':metadata['steps'],
            'duration':metadata['physical_seconds'],'failure':metadata['failure'],'action':'same fixed navigation; learned contact/recovery choices',
            'selection':{'checkpoint_id':cp['checkpoint_id'],'optimizer_updates':u}}}
    manifest['results'].append({'cohort':'Continuous task-model development','method':label,'qualified':int(metadata['qualified_complete']),
        'n':1,'mean_steps':metadata['steps'] if metadata['qualified_complete'] else None})
with volume.batch_upload() as batch:
    for path,destination in uploads:batch.put_file(path,destination)
case['comparison_note']='All four saved task checkpoints are available in the selectors. Update 8 qualified in 817 steps; updates 4 and 16 qualified in 848. The parent missed laptop-leg sole clearance. These are controlled development results; final layouts remain unopened.'
manifest['claim']='Development preview. Selected task checkpoint 8 qualifies in the continuous four-task sequence; the parent misses a quality limit. Navigation training continues with a compact two-profile interface. No fresh-layout advantage is claimed yet.'
manifest['training']='32 original navigation and 16 separate task/recovery optimizer updates are completed. Task checkpoint 8 was selected using actual uninterrupted development runs. The next navigation curriculum uses compact planner summaries and the direct/buffered controllers; its remaining 16 updates have not started.'
target.write_text(json.dumps(manifest,indent=2)+'\n')
(directory/'preview-manifest-r4.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'task_checkpoints':[0,4,8,16],'selected':8,'steps':817,'qualified':True,'final_opened':False}))
