"""Add all continuous task attempts and the preserved engineering progression."""
import gzip
import hashlib
import json
from pathlib import Path
import modal
from mochi.smooth_v16.public import rounded

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
web=root/'web/desk/continuation-v25';target=web/'manifest.json'
manifest=json.loads(target.read_text());run=manifest['run_id']
manifest['cases']=[c for c in manifest['cases'] if c['id'] not in ['task-weight-development','task-development']]
manifest['claim']=manifest['claim'].replace(' Four-task checkpoint replays below are development evidence; the new combined-model cohort is separate.','')
manifest['training']=manifest['training'].replace(' Four-task final results are pending.','')
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
report=json.loads(b''.join(volume.read_file(run+'/task-training.json')))
assert report['status']=='completed'
selection=json.loads((directory/'task-selection-freeze.json').read_text())
development=json.loads((directory/'task-development-continuous.json').read_text())
final=json.loads((directory/'task-final-continuous.json').read_text())
assert len(final['results'])==12
uploads=[]
def recording(metadata,label):
    ident=metadata['id'];raw=(directory/(ident+'.json.gz')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==metadata['sha256']
    row=json.loads(gzip.decompress(raw));episode=row['episode']
    public={k:v for k,v in episode.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
    public['balance_measurements']=[{k:v for k,v in r.items() if k in ['t','phase','roll_rad','loads_n','step_category']} for r in episode['balance_measurements']]
    public['model_decisions']=episode['decisions']
    packed=gzip.compress(json.dumps(rounded(public),separators=(',',':')).encode(),mtime=0)
    name=ident+'.json.gz';path=directory/('public-'+name)
    if path.exists():assert path.read_bytes()==packed
    else:path.write_bytes(packed)
    uploads.append((path,'/'+run+'/public/'+name))
    sha=hashlib.sha256(packed).hexdigest()
    manifest['recordings'][name]={'path':run+'/public/'+name,'sha256':sha,'bytes':len(packed)}
    settings=metadata['policy_settings'];u=settings['task']['update']
    cp=next(c for c in report['checkpoints'] if c['update']==u)
    nav=settings['navigation'];nav_label='fixed' if nav['mode']=='fixed' else str(nav['update'])
    return {'file':name,'sha256':sha,'label':label,'updates':f'navigation {nav_label}; task {u}',
        'row':{'kind':'sequence','qualified_complete':row['qualified_complete'],'steps':metadata['steps'],
            'duration':metadata['physical_seconds'],'failure':row['failure'],
            'action':f'navigation {nav_label}; task checkpoint {u}',
            'selection':{'checkpoint_id':cp['checkpoint_id'],'optimizer_updates':f'nav {nav_label}, task {u}'},
            'checkpoint_decisions':metadata['checkpoint_decisions']}}

runs={}
for row in development['results']:
    u=row['task_checkpoint_update'];key='parent' if u==0 else 'selected' if u==selection['selected_update'] else 'u'+str(u)
    runs[key]=recording(row,'Task checkpoint · update '+str(u))
if 'selected' not in runs:runs['selected']=runs['parent']
manifest['cases'].append({'id':'task-development','label':'Continuous four-task development · all checkpoints','kind':'sequence','split':'development',
    'layout_sha256':development['results'][0]['layout_sha256'],'runs':runs,
    'scope':'Actual uninterrupted checkpoint rollouts, same reset and fixed navigation wrapper. No state restoration or stitching.',
    'comparison_note':'The continuous development criterion selected task checkpoint '+str(selection['selected_update'])+'. The component-only choice was provisional.'})
for i in range(3):
    for seed in [253000,253001]:
        pair=[r for r in final['results'] if r['id'].startswith('task-final-'+str(i)+'-'+str(seed)+'-')]
        assert len(pair)==2 and pair[0]['layout_sha256']==pair[1]['layout_sha256']
        runs={}
        for row in pair:
            side=row['id'].rsplit('-',1)[1]
            runs[side]=recording(row,'Parent models' if side=='parent' else 'Selected models')
        manifest['cases'].append({'id':f'task-final-{i}-{seed}','label':f'Fresh four-task layout {i+1} · seed {seed}',
            'kind':'sequence','split':'final','layout_sha256':pair[0]['layout_sha256'],'runs':runs,
            'scope':'One continuous clock, drawer, laptop and globe rollout per side. Same scene, reset, R5 controller, Modal CPU runtime and checks. Models frozen before this cohort.',
            'comparison_note':'All six fresh scenario pairs remain available, including failures. A successful example does not replace the complete cohort.'})
for side in ['parent','selected']:
    rows=[r for r in final['results'] if r['id'].endswith('-'+side)];valid=[r for r in rows if r['qualified_complete']]
    manifest['results'].append({'cohort':'Fresh continuous four-task layouts','method':side.title()+' models','qualified':len(valid),'n':len(rows),
        'mean_steps':sum(r['steps'] for r in valid)/len(valid) if valid else None})
preview=json.loads((directory/'preview-manifest-r2.json').read_text())
for case in preview['cases']:
    if case['split']=='engineering' and not any(c['id']==case['id'] for c in manifest['cases']):manifest['cases'].append(case)
for name,entry in preview['recordings'].items():
    if name.startswith('engineering-'):manifest['recordings'][name]=entry
manifest['checkpoints']=[c for c in manifest['checkpoints'] if c['domain']!='task and recovery']+[dict(c,domain='task and recovery') for c in report['checkpoints']]
selected_rows=[r for r in final['results'] if r['id'].endswith('-selected')]
n=sum(r['qualified_complete'] for r in selected_rows)
manifest['claim']+=f' The selected models qualified on {n}/6 uninterrupted four-task attempts across three fresh arrangements.'
manifest['training']+=' A separate task and recovery adapter completed 16 actual optimizer updates from measured component alternatives. Continuous development rollouts selected its checkpoint.'
seen={s['url'] for query in manifest['sources'] for s in query['sources']}
for query in report['services']['sources']:
    unique=[]
    for source in query['sources']:
        if source['url'] not in seen:
            seen.add(source['url']);unique.append(source)
    if unique:manifest['sources'].append(dict(query,sources=unique))
manifest['task_selection']={'selected_update':selection['selected_update'],'qualified_final':n,'n_final':6,
    'scope':'Three task arrangements, two seeds each. Layouts are the independent sampling units.'}
usage=modal.Dict.from_name('mochi-continuation-v25-budget')[run]['usage']
manifest['execution']=f'{usage["physical_rollouts"]} charged physical attempts; {usage["simulation_cpu_hours"]:.2f} summed simulation wall hours, including any conservative reservations, at this snapshot. Final task workers started after navigation completed, with a maximum of five physical workers. Costs are modeled, not invoices.'
for total in manifest['totals']:
    if total[1]=='charged physical attempts':total[0]=usage['physical_rollouts']
if not any(row[1]=='completed task and recovery optimizer updates' for row in manifest['totals']):manifest['totals'].append([16,'completed task and recovery optimizer updates'])
with volume.batch_upload() as batch:
    for path,destination in uploads:batch.put_file(path,destination)
target.write_text(json.dumps(manifest,separators=(',',':'))+'\n')
evidence=root/'evidence/continuation-v25'
(evidence/'task-continuous-results.json').write_text(json.dumps({'selection':selection,'development':development,'final':final},indent=2)+'\n')
print(json.dumps({'fresh_selected_qualified':n,'n':6,'cases':len(manifest['cases']),'recordings':len(manifest['recordings'])}))
