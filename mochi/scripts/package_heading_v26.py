"""Engineering comparisons and explicitly single-model prospective validation."""
import gzip
import hashlib
import json
from pathlib import Path
import modal
from mochi.smooth_v16.public import rounded
from mochi.navigation_v25.qualification_report_v26 import quality_misses

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
target=root/'web/desk/continuation-v25/manifest.json';manifest=json.loads(target.read_text());run=manifest['run_id']
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
training=json.loads(b''.join(volume.read_file(run+'/task-training.json')))
checkpoint=next(c for c in training['checkpoints'] if c['update']==8)
config=json.loads((root/'configs/paperfree-v19-training.json').read_text());uploads=[]
manifest['cases']=[c for c in manifest['cases'] if not c['id'].startswith('heading26-')]
manifest['results']=[r for r in manifest['results'] if r['cohort']!='Prospective heading-aware product validation']

def recording(metadata,label):
    raw=(directory/(metadata['id']+'.json.gz')).read_bytes();assert hashlib.sha256(raw).hexdigest()==metadata['sha256']
    row=json.loads(gzip.decompress(raw));e=row['episode']
    public={k:v for k,v in e.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
    public['balance_measurements']=[{k:v for k,v in r.items() if k in ['t','phase','roll_rad','loads_n','step_category']} for r in e['balance_measurements']]
    public['model_decisions']=e['decisions'];packed=gzip.compress(json.dumps(rounded(public),separators=(',',':')).encode(),mtime=0)
    name=metadata['id']+'.json.gz';path=directory/('public-'+name);sha=hashlib.sha256(packed).hexdigest()
    if path.exists():assert path.read_bytes()==packed
    else:path.write_bytes(packed)
    if name not in manifest['recordings']:uploads.append((path,'/'+run+'/public/'+name))
    else:assert manifest['recordings'][name]['sha256']==sha
    manifest['recordings'][name]={'path':run+'/public/'+name,'sha256':sha,'bytes':len(packed)}
    laptop=e['results'].get('laptop',{});misses=quality_misses(row,config)
    display=row['failure'] or '; '.join(misses[:2]) or None
    if row['failure']=='laptop-failed:laptop' and laptop.get('abort')=='force_limit':display='laptop contact exceeded the 0.8 N limit'
    return {'file':name,'sha256':sha,'label':label,'updates':'navigation 48; task 8','row':{
        'kind':'sequence','qualified_complete':row['qualified_complete'],'steps':metadata['steps'],'duration':metadata['physical_seconds'],
        'failure':row['failure'],'display_failure':display,'laptop_peak_force_n':laptop.get('max_force_n'),'quality_misses':misses,
        'action':'navigation 48; task 8; '+metadata['engineering_revision'],
        'selection':{'checkpoint_id':checkpoint['checkpoint_id'],'optimizer_updates':'nav 48, task 8'},'physical_source_sha256':metadata['source_freeze_sha256']}}

development=[json.loads((directory/f'contact26r{revision}-dev-selected.metadata.json').read_text()) for revision in [3,4]]
assert all(r['status']=='completed' for r in development)
assert development[0]['layout_sha256']==development[1]['layout_sha256']
manifest['cases'].append({'id':'heading26-development','label':'Tracking-clearance engineering · identical model weights','kind':'sequence','split':'development',
    'layout_sha256':development[0]['layout_sha256'],'runs':{'parent':recording(development[0],'R3 · nominal oriented route'),'selected':recording(development[1],'R4 · tracking-clearance route')},
    'scope':'Engineering comparison on the same opened development arrangement and seed. Both sides use frozen navigation-48/task-8 weights. Controllers differ; no extra optimizer update. Each recording is one uninterrupted physical attempt.',
    'comparison_note':'This comparison measures planner/controller engineering. It does not establish a model-weight gain. All original physical quality checks are unchanged.'})
if development[1]['qualified_complete']:manifest['default_case']='heading26-development'
product=directory/'heading26-product-final.json';report=json.loads(product.read_text()) if product.exists() else None
if report:
    assert len(report['results'])==3
    for i,metadata in enumerate(report['results']):
        manifest['cases'].append({'id':f'heading26-final-{i}','label':f'Heading-aware validation · new layout {i+1}','kind':'sequence','split':'final','single_validation':True,
            'layout_sha256':metadata['layout_sha256'],'runs':{'selected':recording(metadata,'Frozen navigation 48 / task 8')},
            'scope':'One selected-model first attempt on a new arrangement and physics seed. Both panes show the same physical rollout from different cameras. No parent-model comparison. Shared R4 engineering; no additional training.',
            'comparison_note':'Prospective product validation. These outcomes cannot establish a model-weight or memory benefit. All three attempts, including failures, remain available.'})
    good=[r for r in report['results'] if r['qualified_complete']]
    manifest['results'].append({'cohort':'Prospective heading-aware product validation','method':'Frozen nav 48 / task 8 + R4 engineering','qualified':len(good),'n':3,'mean_steps':sum(r['steps'] for r in good)/len(good) if good else None})
    manifest['heading_product_validation']={'qualified':len(good),'n':3,'scope':report['scope'],'source_sha256':report['source_freeze_sha256']}
    manifest.setdefault('claim_before_heading_validation',manifest['claim'])
    manifest['claim']=manifest['claim_before_heading_validation']+f' A separate prospective R4 engineering validation qualified on {len(good)}/3 new selected-model attempts. This is not a model-weight comparison.'
research=json.loads((root/'evidence/continuation-v25/heading-research.json').read_text());seen={s['url'] for q in manifest['sources'] for s in q['sources']}
for query in research['services']['sources']:
    sources=[dict(s,excerpt=' '.join(s.get('excerpt','').split()[:10])) for s in query['sources'] if s['url'] not in seen]
    if sources:manifest['sources'].append(dict(query,sources=sources));seen.update(s['url'] for s in sources)
usage=modal.Dict.from_name('mochi-continuation-v25-budget')[run]['usage']
for total in manifest['totals']:
    if total[1]=='charged physical attempts':total[0]=usage['physical_rollouts']
manifest['execution']=f'{usage["physical_rollouts"]} charged physical attempts; {usage["simulation_cpu_hours"]:.2f} summed simulation wall hours. Actual optimizer updates remain 64. Provider and architecture are retained per attempt. Costs are modeled, not invoices.'
with volume.batch_upload() as batch:
    for path,destination in uploads:batch.put_file(path,destination)
target.write_text(json.dumps(manifest,separators=(',',':'))+'\n')
evidence=root/'evidence/continuation-v25'
(evidence/'heading-continuation-results.json').write_text(json.dumps({'development':development,'product':report,'usage':usage},indent=2)+'\n')
print(json.dumps({'cases':len(manifest['cases']),'development_qualified':development[1]['qualified_complete'],'product':manifest.get('heading_product_validation')}))
