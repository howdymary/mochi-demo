"""A complete, labeled development comparison while final evaluation waits."""
import gzip
import hashlib
import json
from pathlib import Path
import modal
from mochi.smooth_v16.public import rounded

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
target=root/'web/desk/continuation-v25/manifest.json';manifest=json.loads(target.read_text())
assert not any(c['id']=='task-weight-development' for c in manifest['cases'])
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts');run=manifest['run_id']
report=json.loads(b''.join(volume.read_file(run+'/task-training.json')));assert report['status']=='completed'
runs={};uploads=[]
for side,u in [('parent',0),('selected',4)]:
    ident='task-dev-u'+str(u);metadata=json.loads((directory/(ident+'.metadata.json')).read_text())
    raw=(directory/(ident+'.json.gz')).read_bytes();assert hashlib.sha256(raw).hexdigest()==metadata['sha256']
    episode=json.loads(gzip.decompress(raw))['episode']
    public={k:v for k,v in episode.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
    public['balance_measurements']=[{k:v for k,v in r.items() if k in ['t','phase','roll_rad','loads_n','step_category']} for r in episode['balance_measurements']]
    public['model_decisions']=episode['decisions']
    packed=gzip.compress(json.dumps(rounded(public),separators=(',',':')).encode(),mtime=0)
    name='progress-'+ident+'.json.gz';local=directory/name;assert not local.exists();local.write_bytes(packed)
    path=run+'/public/'+name;uploads.append((local,'/'+path));sha=hashlib.sha256(packed).hexdigest()
    manifest['recordings'][name]={'path':path,'sha256':sha,'bytes':len(packed)}
    cp=next(c for c in report['checkpoints'] if c['update']==u)
    runs[side]={'file':name,'label':'Parent task weights · update 0' if not u else 'Trained task weights · update 4',
        'sha256':sha,'row':{'kind':'sequence','qualified_complete':metadata['qualified_complete'],'steps':metadata['steps'],
            'duration':metadata['physical_seconds'],'failure':metadata['failure'],'action':'same fixed navigation; learned contact/recovery choices',
            'selection':{'checkpoint_id':cp['checkpoint_id'],'optimizer_updates':u}}}
    manifest['results'].append({'cohort':'Continuous task-model development','method':runs[side]['label'],'qualified':int(metadata['qualified_complete']),
        'n':1,'mean_steps':metadata['steps'] if metadata['qualified_complete'] else None})
    if side=='parent':layout=metadata['layout_sha256']
    else:assert layout==metadata['layout_sha256']
with volume.batch_upload() as batch:
    for local,destination in uploads:batch.put_file(local,destination)
manifest['cases'].insert(0,{'id':'task-weight-development','label':'Four tasks · actual Tinker checkpoint comparison','kind':'sequence','split':'development',
    'layout_sha256':layout,'runs':runs,'scope':'Same physical code, scene, reset and fixed navigation profile. Separate uninterrupted rollouts using actual saved task-model weights.',
    'comparison_note':'The parent completed the tasks but missed laptop-leg sole clearance: 4.395 mm versus the frozen 4.5 mm limit. Update 4 qualified, with 4.818 mm. Failed runs do not count toward efficiency gains. Checkpoints 8 and 16 are still being evaluated; final task layouts remain unopened.'})
manifest['default_case']='task-weight-development'
manifest['summary']='A saved Tinker task checkpoint completes the continuous four-task sequence under every quality check. Fresh-layout navigation evaluation continues.'
manifest['claim']='Development preview. Update 4 qualified where the parent missed laptop-leg foot clearance. No advantage over the fixed navigation strategy or fresh-task reliability is claimed yet.'
manifest['training']+=' A separate contact/recovery adapter completed 16 real optimizer updates. Its update-4 checkpoint is shown here; continuous selection is not finished.'
manifest['checkpoints'] += [dict(c,domain='task and recovery') for c in report['checkpoints']]
manifest['totals'].append([16,'completed task and recovery optimizer updates'])
target.write_text(json.dumps(manifest,indent=2)+'\n')
(directory/'preview-manifest-r3.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'cases':len(manifest['cases']),'recordings':len(manifest['recordings']),'task_comparison':'same-controller actual checkpoint weights'}))
