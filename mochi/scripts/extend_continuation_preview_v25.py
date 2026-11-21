"""Add a matched book-descent repair without attributing it to training."""
import gzip
import hashlib
import json
from pathlib import Path
import modal
from mochi.smooth_v16.public import rounded

root=Path(__file__).resolve().parents[1]
directory=root/'artifacts/continuation-v25'
target=root/'web/desk/continuation-v25/manifest.json'
manifest=json.loads(target.read_text())
assert not any(c['id']=='descent-engineering' for c in manifest['cases'])
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
runs={}
for side,ident in [('parent','sequence-train-firm-r5'),('selected','sequence-balanced-descent-r6')]:
    row=json.loads(gzip.decompress((directory/(ident+'.json.gz')).read_bytes()))
    metadata=json.loads((directory/(ident+'.metadata.json')).read_text())
    episode=row['episode']
    public={k:v for k,v in episode.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
    public['balance_measurements']=[{k:v for k,v in r.items() if k in ['t','phase','roll_rad','loads_n','step_category']} for r in episode['balance_measurements']]
    public['model_decisions']=episode['decisions']
    packed=gzip.compress(json.dumps(rounded(public),separators=(',',':')).encode(),mtime=0)
    name='engineering-'+ident+'.json.gz';local=directory/name
    assert not local.exists();local.write_bytes(packed)
    path=manifest['run_id']+'/public/'+name
    with volume.batch_upload() as batch:batch.put_file(local,'/'+path)
    sha=hashlib.sha256(packed).hexdigest()
    manifest['recordings'][name]={'path':path,'sha256':sha,'bytes':len(packed)}
    label='Earlier descent timing · engineering' if side=='parent' else 'Slower support transfer · engineering'
    runs[side]={'file':name,'label':label,'sha256':sha,'fingerprint':metadata['source_sha256'],'updates':0,
        'row':{'kind':'sequence','qualified_complete':row['qualified_complete'],'steps':episode['steps']['attempts'],
            'duration':episode['duration'],'failure':row['failure'],'action':'fixed task profiles; shared descent repair'}}
    manifest['results'].append({'cohort':'Matched book-descent repair','method':label,'qualified':int(row['qualified_complete']),
        'n':1,'mean_steps':episode['steps']['attempts'] if row['qualified_complete'] else None})
    if side=='parent':layout=metadata['layout_sha256']
    else:assert layout==metadata['layout_sha256']
manifest['cases'].append({'id':'descent-engineering','label':'Four-task sequence · book-descent repair','kind':'sequence','split':'engineering',
    'layout_sha256':layout,'runs':runs,'scope':'Same arrangement and physics seed, uninterrupted runs from reset. Only descent timing changes; zero training updates credited.',
    'comparison_note':'The earlier run fell during book descent. Slower support transfer completed all four tasks and passed the unchanged quality checks. Failed attempts are retained; their short duration is not an efficiency gain.'})
manifest['cases'][1]['comparison_note']='The earlier run completed the tasks but missed the globe-leg sole-clearance limit. The repaired run qualified in 752 steps. A separate matched descent comparison preserves the subsequent fall and its repair.'
manifest['totals'][-1]=[3,'qualified controller-development sequences']
manifest['claim']='Progress preview. The trained model has not yet demonstrated the fixed-strategy goal on fresh layouts. Three qualified controller-development sequences do not establish fresh-layout task reliability.'
manifest['uncertainty']='One known training-layout checkpoint probe and two shared-controller comparisons. The final navigation and task layouts remain unopened.'
target.write_text(json.dumps(manifest,indent=2)+'\n')
(directory/'preview-manifest-r2.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'cases':len(manifest['cases']),'recordings':len(manifest['recordings'])}))
