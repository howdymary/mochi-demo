"""Freeze two-profile labels and audit exact deterministic development reuse."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,RUN

app=modal.App('mochi-navigation-v25-compact-preparation')
@app.function(image=image,serialized=True,cpu=1,memory=4096,timeout=900,retries=0,volumes={'/artifacts':volume})
def build():
    from collections import Counter
    import gzip
    import hashlib
    from mochi.integrations import digest
    from mochi.navigation_v25.compact import ACTIONS
    from mochi.navigation_v25.compact_baselines import tune
    from mochi.navigation_v25.compact_baselines import contextual
    from mochi.navigation_v25.baselines import comparison
    volume.reload();directory=Path('/artifacts')/RUN;out=directory/'compact';out.mkdir(exist_ok=True)
    assert not (out/'data.json').exists()
    prior=json.loads((directory/'collection-training24.json').read_text())
    records=[]
    for original in prior['records']:
        r={**original,'outcomes':{a:original['outcomes'][a] for a in ACTIONS}}
        valid=[a for a in ACTIONS if all(x['qualified'] for x in r['outcomes'][a])]
        r['target']=min(valid,key=lambda a:(sum(x['steps']['attempts'] for x in r['outcomes'][a]),sum(x['physical_seconds'] for x in r['outcomes'][a]))) if valid else None
        records.append(r)
    training=json.loads(Path('/app/configs/continuation-v25/training.json').read_text())
    for i in range(24,32):
        rows=[]
        for seed in [251000,251001]:
            for a in ACTIONS:
                p=directory/'physics'/f'compact-train-{i}-{seed}-{a}.summary.json'
                row=json.loads(p.read_text());assert row['request_sha256']==digest([training[i],seed,a,{}])
                assert row['receipt']['provider']=='Local CPU'
                for entry in [row['artifact'],row['public_recording']]:
                    assert hashlib.sha256((Path('/artifacts')/entry['path']).read_bytes()).hexdigest()==entry['sha256']
                rows.append(row)
        assert len({r['receipt']['architecture'] for r in rows})==1
        outcomes={a:[r for r in rows if r['action']==a] for a in ACTIONS}
        valid=[a for a in ACTIONS if all(r['qualified'] for r in outcomes[a])]
        winner=min(valid,key=lambda a:(sum(r['steps']['attempts'] for r in outcomes[a]),sum(r['physical_seconds'] for r in outcomes[a]))) if valid else None
        records.append({'layout_sha256':training[i]['layout_sha256'],'target':winner,
            'observations':[next(r['observation'] for r in rows if r['seed']==seed) for seed in [251000,251001]],
            'outcomes':outcomes})
    development=json.loads(Path('/app/configs/continuation-v25/development.json').read_text())
    available={}
    for p in sorted((directory/'physics').glob('dev-*.summary.json')):
        row=json.loads(p.read_text());key=(row['layout_sha256'],row['seed'],row['action'])
        if row['action'] in ACTIONS:available.setdefault(key,row)
    table=[]
    for layout in development:
        for seed in [251000,251001]:
            outcomes={a:available[(layout['layout_sha256'],seed,a)] for a in ACTIONS}
            assert len({r['initial_physical_state_sha256'] for r in outcomes.values()})==1
            assert len({r['mechanics_sha256'] for r in outcomes.values()})==1
            assert all(r['receipt']['provider']=='Modal' for r in outcomes.values())
            table.append({'layout_sha256':layout['layout_sha256'],'seed':seed,
                'observation':outcomes['direct']['observation'],'outcomes':outcomes})
    audit=[]
    for seed in [251000,251001]:
        paths=[directory/'physics'/f'dev-{name}-6-{seed}.json.gz' for name in ['contextual','u0']]
        rows=[json.loads(gzip.decompress(p.read_bytes())) for p in paths]
        assert rows[0]['action']==rows[1]['action'] and rows[0]['initial_physical_state_sha256']==rows[1]['initial_physical_state_sha256']
        fields=['trajectory','control_telemetry','step_events','balance_measurements']
        hashes={f:[digest(r['episode'][f]) for r in rows] for f in fields}
        assert all(h[0]==h[1] for h in hashes.values()),'Exact deterministic reuse audit failed; require fresh physical development runs'
        audit.append({'seed':seed,'source_files':[str(p.relative_to('/artifacts')) for p in paths],'exact_field_hashes':hashes})
    fit=tune(records)
    reference=[c['outcomes'][fit['fixed']] for c in table]
    oracle=[min(c['outcomes'].values(),key=lambda r:(not r['qualified'],r['steps']['attempts'] if r['qualified'] else float('inf'))) for c in table]
    conditional=[c['outcomes'][contextual(c['observation'],fit['contextual'])] for c in table]
    data={'records':records,'targets':dict(Counter(r['target'] for r in records)),'baselines':fit,
        'development_table':table,'determinism_audit':audit,'final_opened':False,
        'final_set_sha256':json.loads(Path('/app/configs/continuation-v25/navigation-splits.json').read_text())['final_navigation']['sha256'],
        'scope':'32 training layouts, two seeds, two retained profiles. Original 24 retargeted from real outcomes; eight additional layouts physically evaluated. Development outcome reuse is explicit and exact-trajectory audited. Final evaluation requires new physical runs.'}
    (out/'data.json').write_text(json.dumps(data,indent=2)+'\n')
    result={'training_layouts':len(records),'targets':data['targets'],'data_sha256':digest(data),
        'development_states':len(table),'exact_reuse_pairs':len(audit),'baselines':data['baselines'],'final_opened':False,
        'development_contextual_against_fixed':comparison(reference,conditional),
        'development_oracle_upper_bound':comparison(reference,oracle),
        'oracle_caveat':'Uses development outcomes to check attainability. Never a policy observation, training label or claimed deployed result.'}
    (out/'data-freeze.json').write_text(json.dumps(result,indent=2)+'\n');volume.commit();return result

@app.local_entrypoint()
def main():
    result=build.remote();root=Path(__file__).resolve().parents[1]
    (root/'artifacts/continuation-v25/compact-data-freeze.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
