"""Recover the teacher table from completed, immutable request artifacts."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,RUN

app=modal.App('mochi-v25-cache-recovery')


@app.function(image=image,serialized=True,cpu=1,memory=2048,timeout=600,retries=0,volumes={'/artifacts':volume})
def rebuild():
    from collections import Counter
    import hashlib
    from mochi.integrations import digest,now
    from mochi.navigation_v25.engine import ACTIONS
    volume.reload()
    directory=Path('/artifacts')/RUN
    target=directory/'collection-training24.json'
    prior=json.loads(target.read_text());assert prior['status']=='incomplete'
    layouts=json.loads(Path('/app/configs/continuation-v25/training.json').read_text())[:24]
    report={'status':'completed','at':now(),'layouts_requested':24,'completed_attempts':[],
        'records':[],'targets':{},'scope':'Three profiles, two seeds. Reassembled from 144 already completed requests; zero new physical rollouts in this recovery.'}
    for i,layout in enumerate(layouts):
        rows=[]
        for seed in [251000,251001]:
            for action in ACTIONS:
                ident=f'r1-train-{i}-{seed}-{action}'
                row=json.loads((directory/'physics'/(ident+'.summary.json')).read_text())
                assert row['request_sha256']==digest([layout,seed,action,{}])
                assert row['receipt']['provider']==('Modal' if i<4 else 'Local CPU')
                for entry in [row['artifact'],row['public_recording']]:
                    p=Path('/artifacts')/entry['path']
                    assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],entry['path']
                rows.append(row)
                report['completed_attempts'].append({'id':ident,'qualified':row['qualified'],
                    'steps':row['steps']['attempts'],'wall_seconds':row['receipt']['duration_seconds'],'provider':row['receipt']['provider']})
        assert len({r['receipt']['architecture'] for r in rows})==1
        groups={a:[r for r in rows if r['action']==a] for a in ACTIONS}
        valid=[a for a in ACTIONS if all(r['qualified'] for r in groups[a])]
        winner=min(valid,key=lambda a:(sum(r['steps']['attempts'] for r in groups[a]),sum(r['physical_seconds'] for r in groups[a]))) if valid else None
        report['records'].append({'layout_sha256':layout['layout_sha256'],'target':winner,
            'observations':[next(r['observation'] for r in rows if r['seed']==seed) for seed in [251000,251001]],
            'outcomes':{a:[{k:r[k] for k in ['seed','qualified','checks','steps','physical_seconds','fall','invalid_contact','reward','public_recording','artifact','receipt']} for r in groups[a]] for a in ACTIONS}})
    report['targets']=dict(Counter(r['target'] for r in report['records']))
    report['data_sha256']=digest(report['records'])
    archived=directory/'diagnostics/interrupted-r0/collection-before-materialization.json'
    archived.parent.mkdir(parents=True,exist_ok=True);assert not archived.exists();archived.write_text(target.read_text())
    target.write_text(json.dumps(report,indent=2)+'\n');volume.commit()
    return {'status':'completed','requests':len(report['completed_attempts']),'targets':report['targets'],
        'data_sha256':report['data_sha256'],'physical_rollouts_in_recovery':0}


@app.local_entrypoint()
def launch():
    result=rebuild.remote()
    root=Path(__file__).resolve().parents[1]
    (root/'artifacts/continuation-v25/data-recovery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
