"""Measured multi-seed targets and resumable, equal-budget profile evaluation."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image, volume, RUN

ROOT = Path(__file__).resolve().parents[1]
app = modal.App('mochi-navigation-v25-collection')


@app.function(image=image, serialized=True, cpu=1, memory=4096, timeout=21600,
    max_containers=1, retries=0, volumes={'/artifacts': volume})
async def collect(count, name):
    import asyncio
    import hashlib
    from collections import Counter
    from mochi.navigation_v25.engine import ACTIONS
    from mochi.integrations import now
    broker = modal.Function.from_name('mochi-continuation-v25','budget')
    trial = modal.Function.from_name('mochi-continuation-v25','trial')
    layouts = json.loads(Path('/app/configs/continuation-v25/training.json').read_text())[:count]
    assert len(layouts)==count and count<=32 and name.replace('-','').isalnum()
    directory=Path('/artifacts')/RUN
    directory.mkdir(exist_ok=True)
    target=directory/('collection-'+name+'.json')
    if target.exists():
        prior=json.loads(target.read_text())
        assert prior['layouts_requested']==count
        if prior['status']=='completed':return {'status':'completed','layouts':count,'targets':prior['targets']}
        archived=target.with_name(target.stem+'-interrupted-r0.json')
        if not archived.exists():archived.write_text(target.read_text())
        # Rebuild from immutable, assigned request caches. No completed physical
        # input is intentionally rerun; the worker waits for local producers.

    report={'status':'running','at':now(),'layouts_requested':count,'completed_attempts':[],
        'records':[],'targets':{},'scope':'Three profiles, two physics seeds. Qualification across both seeds outranks efficiency.'}
    slots=asyncio.Semaphore(4)
    async def save():
        target.write_text(json.dumps(report,indent=2)+'\n');await volume.commit.aio()
    async def one(i,layout,seed,action):
        async with slots:
            ident=f'r1-train-{i}-{seed}-{action}'
            await broker.remote.aio(RUN,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1,'modeled_provider_usd':.02})
            row=await trial.remote.aio(layout,seed,action,{},ident)
            await broker.remote.aio(RUN,ident+'-actual',{'simulation_cpu_hours':row['receipt']['duration_seconds']/3600-.1})
            report['completed_attempts'].append({'id':ident,'qualified':row['qualified'],
                'steps':row['steps']['attempts'],'wall_seconds':row['receipt']['duration_seconds']})
            await save()
            return row
    try:
        await save()
        for i,layout in enumerate(layouts):
            rows=await asyncio.gather(*(one(i,layout,seed,action) for seed in [251000,251001] for action in ACTIONS))
            groups={a:[r for r in rows if r['action']==a] for a in ACTIONS}
            valid=[a for a in ACTIONS if all(r['qualified'] for r in groups[a])]
            winner=min(valid,key=lambda a:(sum(r['steps']['attempts'] for r in groups[a]),sum(r['physical_seconds'] for r in groups[a]))) if valid else None
            record={'layout_sha256':layout['layout_sha256'],'target':winner,
                'observations':[next(r['observation'] for r in rows if r['seed']==seed) for seed in [251000,251001]],
                'outcomes':{a:[{k:r[k] for k in ['seed','qualified','checks','steps','physical_seconds','fall','invalid_contact','reward','public_recording','artifact','receipt']} for r in groups[a]] for a in ACTIONS}}
            report['records'].append(record)
            report['targets']=dict(Counter(r['target'] for r in report['records']))
            await save()
            print(json.dumps({'layouts':len(report['records']),'attempts':len(report['completed_attempts']),'targets':report['targets']}),flush=True)
        report['status']='completed'
        report['data_sha256']=hashlib.sha256(json.dumps(report['records'],sort_keys=True).encode()).hexdigest()
        await save()
        return {'status':'completed','layouts':count,'targets':report['targets']}
    except BaseException as error:
        report.update(status='incomplete',error_type=type(error).__name__);await save();raise


@app.local_entrypoint()
def launch(count:int=2,name:str='pilot'):
    out=ROOT/'artifacts/continuation-v25'/('collection-'+name+'-launch.json')
    assert not out.exists()
    call=modal.Function.from_name('mochi-navigation-v25-collection','collect').spawn(count,name)
    out.write_text(json.dumps({'call_id':call.object_id,'run_id':RUN,'count':count,'name':name},indent=2)+'\n')
    print(json.dumps({'call_id':call.object_id,'count':count,'name':name,'detached':True}))
