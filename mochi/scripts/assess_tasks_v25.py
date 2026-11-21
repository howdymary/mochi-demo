"""Summarize all frozen final task attempts, pairing within layout and seed."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
d=root/'artifacts/continuation-v25'
source=d/'task-final-continuous.json'
cohort=json.loads(source.read_text())
assert len(cohort['results'])==12
models={s:[] for s in ['parent','selected']}
for metadata in cohort['results']:
    raw=(d/(metadata['id']+'.json.gz')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==metadata['sha256']
    row=json.loads(gzip.decompress(raw));e=row['episode']
    models[metadata['id'].rsplit('-',1)[1]].append(dict(metadata,
        seed=row['seed'],recovery_arm_travel_rad=sum(r['arm_joint_travel_rad'] for r in e['recoveries']),
        intertask_arm_travel_rad=sum(e['intertask_arm_joint_travel_rad'].values()),
        moving_distance_m=row['direction_metrics']['moving_distance_m'],
        forward_facing_fraction=row['direction_metrics']['forward_facing_fraction']))
result={'scope':'Three final task layouts, two seeds each. All attempts included. These are controller-selection weights around a shared engineered controller. Native gait fixed.',
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'engineering_revision':cohort['engineering_revision'],'models':{}}
for side,rows in models.items():
    assert len(rows)==6
    result['models'][side]={'n':6,'layouts':len({r['layout_sha256'] for r in rows}),
        'all_tasks_completed':sum(r['complete_sequence_success'] for r in rows),
        'qualified':sum(r['qualified_complete'] for r in rows),'falls':sum(r['fall'] for r in rows),
        'forbidden_contacts':sum(r['invalid_contact'] for r in rows),
        'per_task_completed':{task:sum(r['tasks'].get(task,False) for r in rows) for task in ['alarm','drawer','laptop','globe']},
        'attempts':[{k:r[k] for k in ['id','qualified_complete','failure','steps','physical_seconds','recovery_arm_travel_rad','intertask_arm_travel_rad','flat_legs']} for r in rows]}
a={(r['layout_sha256'],r['seed']):r for r in models['parent']}
b={(r['layout_sha256'],r['seed']):r for r in models['selected']}
assert a.keys()==b.keys()
for key in a:assert a[key]['source_freeze_sha256']==b[key]['source_freeze_sha256']
paired={};pairs=0
for key in a:
    x,y=a[key],b[key]
    if not (x['qualified_complete'] and y['qualified_complete']):continue
    pairs+=1;paired.setdefault(key[0],[]).append((x,y))
metrics={}
for field in ['steps','physical_seconds','recovery_arm_travel_rad','intertask_arm_travel_rad','moving_distance_m']:
    ratios=[]
    for values in paired.values():
        denominator=np.mean([x[field] for x,y in values])
        if denominator>0:ratios.append(float(np.mean([y[field] for x,y in values])/denominator))
    interval=None
    if ratios:
        rng=np.random.default_rng(252819);indices=rng.integers(0,len(ratios),size=(10000,len(ratios)))
        interval=np.quantile(np.asarray(ratios)[indices].mean(axis=1),[.025,.975]).tolist()
    metrics[field]={'mean_layout_ratio':float(np.mean(ratios)) if ratios else None,
        'layout_bootstrap_95_percent_interval':interval}
result['paired']={'jointly_qualified_pairs':pairs,'layouts':len(paired),'metrics':metrics,
    'scope':'Ratios use jointly qualified attempts only, averaged within layout. Three layouts are a small pilot; repeated seeds are not independent layouts. Early failures never count as efficient.'}
result['selected_completed_all_six_smoothly']=result['models']['selected']['qualified']==6
out=root/'evidence/continuation-v25/task-final-assessment.json'
assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['selected_completed_all_six_smoothly','paired']}))
