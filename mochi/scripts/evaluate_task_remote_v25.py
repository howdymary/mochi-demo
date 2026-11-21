"""Matched R5 task evaluation on bounded Modal CPU workers.

Development is mandatory before the unopened task cohort. Saved weights stay
frozen; this experiment changes a shared task controller, not the gait network.
"""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image, volume, RUN, existing_secrets

root=Path(__file__).resolve().parents[1]
app=modal.App('mochi-task-evaluation-v25-r5')


@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=.25,memory=1024,
    timeout=900,max_containers=1,retries=0,volumes={'/artifacts':volume})
async def record_repair(packet):
    from mochi.navigation_v23.services import NavigationServices
    await volume.reload.aio()
    folder=Path('/artifacts')/RUN/'task-clearance-memory'
    done=folder/'completed.json'
    if done.exists():return json.loads(done.read_text())
    assert not (folder/'memory-journal.json').exists(),'Inspect interrupted memory writes; never duplicate them'
    broker=modal.Function.from_name('mochi-continuation-v25','budget');ordinal=0
    async def charge(kind,amount):
        nonlocal ordinal
        ordinal+=1
        await broker.remote.aio(RUN,'task-clearance-memory-'+str(ordinal),{kind:amount})
    services=NavigationServices(RUN+'-r5',folder,charge,volume.commit.aio)
    try:
        await services.setup()
        observed=await services.write('experimenter',{'kind':'combined-controller-clearance-failures',
            'observations':packet['observations'],'source_artifacts':packet['artifacts'],
            'qualification':'Development observations only. No final task layout opened.'})
        recalled=await services.read('researcher',observed)
        hypothesis=await services.write('researcher',{'kind':'bounded-station-clearance-hypothesis',
            'evidence':observed,'mechanism':'Increase swing-pad clearance moderately; excessive lift can prevent final pose capture.',
            'component_observation':packet['candidate'],'hypothesis':'The intermediate lift may retain arrival and sole clearance; full uninterrupted development execution is required.'})
        await services.read('designer',hypothesis)
        plan=await services.write('designer',{'kind':'shared-task-controller-preflight-plan','source':hypothesis,
            'revision':'r5','navigation_checkpoint':48,'task_checkpoint':8,
            'plan':'Execute both frozen weight sets on development geometry under identical Modal physics. Open the sealed task cohort only if the selected combination qualifies.',
            'native_gait_weights_trained':False,'engineering_credit_only':True})
        await services.read('experimenter',plan)
        result=services.report();done.write_text(json.dumps(result,indent=2)+'\n');await volume.commit.aio()
        return result
    finally:await services.http.aclose()


@app.function(image=image,serialized=True,cpu=1,memory=4096,timeout=1200,
    max_containers=5,retries=0,volumes={'/artifacts':volume})
def sequence(ident,layout,seed,settings):
    import gzip
    import hashlib
    import platform
    import signal
    import time
    import torch
    from mochi.navigation_v25.tasks_r5 import run
    from mochi.integrations import digest
    torch.set_num_threads(1)
    directory=Path('/artifacts')/RUN/'task-r5'
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/(ident+'.json.gz');meta=directory/(ident+'.metadata.json')
    request=digest([ident,layout,seed,settings,'r5'])
    if meta.exists():
        result=json.loads(meta.read_text());assert result['request_sha256']==request
        assert result.get('status')=='completed','Retained interrupted attempt; do not silently repeat'
        return result
    assert not target.exists(),'Retain an interrupted recording; never overwrite'
    freeze=json.loads(Path('/app/configs/continuation-v25/tasks/physical-freeze-r5.json').read_text())
    for name,expected in freeze['sha256'].items():
        assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==expected,name
    broker=modal.Function.from_name('mochi-continuation-v25','budget')
    broker.remote(RUN,ident+'-r5-modal-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.3})
    started=time.perf_counter();decisions=[]
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Task worker wall ceiling')))
    signal.setitimer(signal.ITIMER_REAL,1100)
    def choose(domain,task,observed,prompt):
        key='navigation' if domain=='navigation' else 'task'
        kind='compact_navigation' if key=='navigation' else 'task'
        picked=modal.Function.from_name('mochi-task-control-v25','choose').remote(
            kind,settings[key]['update'],observed,f'{ident}-{len(decisions)}-{domain}-{task}')
        decisions.append({'domain':domain,'task':task,'selection':picked})
        return picked
    result=dict(id=ident,request_sha256=request,policy_settings=settings,
        engineering_revision='r5',evaluation_partition=layout.get('partition'),layout_sha256=layout['layout_sha256'],
        source_freeze_sha256=hashlib.sha256(json.dumps(freeze,sort_keys=True).encode()).hexdigest(),
        receipt={'provider':'Modal','cpu':1,'memory_mib':4096,'architecture':platform.machine()},
        scope='Uninterrupted actuator-driven rollout from reset. Identical R5 task controller and runtime for both weight sets. Native gait weights fixed.')
    try:
        row=run(layout,seed,choose=choose)
        payload=gzip.compress(json.dumps(row,separators=(',',':')).encode(),compresslevel=1,mtime=0)
        target.write_bytes(payload);e=row['episode']
        result.update(status='completed',sha256=hashlib.sha256(payload).hexdigest(),
            failure=row['failure'],qualified_complete=row['qualified_complete'],complete_sequence_success=row['complete_sequence_success'],
            tasks={k:v['success'] for k,v in e['results'].items()},steps=e['steps']['attempts'],physical_seconds=e['duration'],
            fall=e['fall'],invalid_contact=e['invalid_contact'],contacts=e['contact_failures'],flat_legs=e['flat_legs'],
            checkpoint_decisions=decisions)
    except BaseException as error:
        result.update(status='incomplete',error_type=type(error).__name__,checkpoint_decisions=decisions)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        elapsed=time.perf_counter()-started;result['wall_seconds']=elapsed
        broker.remote(RUN,ident+'-r5-modal-actual',{'simulation_cpu_hours':elapsed/3600-.3,
            'modeled_provider_usd':elapsed*.00002198})
        meta.write_text(json.dumps(result,indent=2)+'\n');volume.commit()
    return result


@app.local_entrypoint()
def evaluate():
    from concurrent.futures import ThreadPoolExecutor
    import gzip
    import hashlib
    from mochi.navigation_v23.layouts import fingerprint
    directory=root/'artifacts/continuation-v25';cfg=root/'configs/continuation-v25/tasks'
    selected=json.loads((directory/'task-selection-freeze.json').read_text())
    nav=json.loads(b''.join(volume.read_file(RUN+'/compact/selection-freeze.json')))
    assert selected['selected_update']==8 and nav['selected_checkpoint']['update']==48
    checkpoint_fingerprint=fingerprint({'navigation':nav,'task':selected})
    def save(name,value):
        p=directory/(name+'.json');raw=json.dumps(value,indent=2)+'\n'
        if p.exists():assert p.read_text()==raw
        else:p.write_text(raw)
        with volume.batch_upload() as batch:batch.put_file(p,'/'+RUN+'/'+name+'.json')
    def attempt(job):
        result=sequence.remote(*job)
        assert result['status']=='completed'
        raw=b''.join(volume.read_file(RUN+'/task-r5/'+result['id']+'.json.gz'))
        assert hashlib.sha256(raw).hexdigest()==result['sha256']
        dest=directory/(result['id']+'.json.gz')
        if dest.exists():assert dest.read_bytes()==raw
        else:dest.write_bytes(raw)
        m=directory/(result['id']+'.metadata.json');text=json.dumps(result,indent=2)+'\n'
        if m.exists():assert m.read_text()==text
        else:m.write_text(text)
        print(json.dumps({k:result[k] for k in ['id','qualified_complete','steps','physical_seconds','flat_legs']}),flush=True)
        return result
    def settings(side):
        return {'navigation':{'mode':'tinker','representation':'compact','update':48 if side=='selected' else 0},
            'task':{'update':8 if side=='selected' else 0}}
    names=['task-integration-parent','task-integration-selected','station-laptop-feedback-r3-probe','station-laptop-feedback-r4-probe']
    packet={'observations':[],'artifacts':[]}
    for name in names:
        file=directory/(name+'.metadata.json');row=json.loads(file.read_text())
        packet['observations'].append({k:row.get(k) for k in ['id','qualified_complete','qualified','physical_failure','moving_median_peak_m','complete_sequence_success']})
        packet['artifacts'].append({'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    candidate=json.loads((directory/'station-laptop-feedback-r5-probe.metadata.json').read_text())
    assert candidate['qualified'],'Do not scale a physically failing component'
    packet['candidate']={k:candidate[k] for k in ['id','qualified','moving_median_peak_m','snapshot_sha256','artifact_sha256']}
    memory=record_repair.remote(packet)
    memory_file=directory/'task-clearance-memory-receipts.json'
    if not memory_file.exists():memory_file.write_text(json.dumps(memory,indent=2)+'\n')
    layout=json.loads((cfg/'development.json').read_text())
    if isinstance(layout,list):assert len(layout)==1;layout=layout[0]
    jobs=[('task-integration-r5-modal-'+side,layout,252000,settings(side)) for side in ['parent','selected']]
    with ThreadPoolExecutor(max_workers=1) as pool:preflight=list(pool.map(attempt,jobs))
    save('task-integration-r5-modal-continuous',{'results':preflight,'engineering_revision':'r5',
        'selected_qualified':preflight[1]['qualified_complete'],'weights_fingerprint':checkpoint_fingerprint})
    assert preflight[1]['qualified_complete'],'Final task layouts remain unopened; inspect retained R5 failure'
    # The one local R2 capture was allowed alongside three navigation and one
    # task-development worker. It must end before final task concurrency is two.
    assert (directory/'task-integration-selected-capture-r2.metadata.json').exists(),'Wait for the retained local capture before scaling task workers'
    # Reallocate the same five-physics-worker ceiling after navigation ends.
    # Until then only the single sequential task-development call is submitted.
    import time
    while True:
        navigation=json.loads(b''.join(volume.read_file(RUN+'/compact/navigation-training.json')))
        assert navigation['status']!='incomplete','Inspect the retained navigation interruption before scheduling more physics'
        if navigation['status']=='completed':break
        time.sleep(10)
    sealed=directory/'sealed/final_tasks.json';layouts=json.loads(sealed.read_text());splits=json.loads((cfg/'splits.json').read_text())
    assert fingerprint(layouts)==splits['final']['sha256']
    save('task-final-opened',{'set_sha256':fingerprint(layouts),'checkpoint_fingerprint':checkpoint_fingerprint,
        'navigation_selected_update':48,'task_selected_update':8,'engineering_revision':'r5',
        'scope':'All three layouts and both seeds. Frozen selected weights and shared R5 controller; no final-outcome tuning.'})
    jobs=[(f'task-final-{i}-{seed}-{side}',layout,seed,settings(side)) for i,layout in enumerate(layouts)
        for seed in splits['final']['physics_seeds'] for side in ['parent','selected']]
    with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(attempt,jobs))
    save('task-final-continuous',{'phase':'final','engineering_revision':'r5','results':results,
        'scope':'Three fresh task arrangements, two seeds, two fixed weight sets. All twelve uninterrupted Modal physical attempts retained.'})
