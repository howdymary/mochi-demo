"""Actual Tinker task/recovery post-training and backend-only checkpoint inference."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,existing_secrets,RUN

root=Path(__file__).resolve().parents[1]
app=modal.App('mochi-task-control-v25')
previous=modal.Volume.from_name('mochi-navigation-v23-artifacts')
mounts={'/artifacts':volume,'/previous':previous.with_mount_options(read_only=True,sub_path='/mochi-nav23-20261121c')}


@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=.25,memory=1024,timeout=120,retries=0)
async def inventory():
    import tinker
    rest=tinker.RestClient()
    page=await rest.list_user_checkpoints(limit=100,offset=0)
    return {'listed':len(page.checkpoints),'total':page.cursor.total_count if page.cursor else len(page.checkpoints),
        'mutations':0,'optimizer_updates':0,'private_paths_exposed':False}


@app.function(image=image,serialized=True,cpu=1,memory=2048,timeout=120,retries=0)
def observe(layout,seed):
    from mochi.navigation_v25.engine import inspect,observation
    w,envelope,obstacles,plans=inspect(layout,seed)
    return observation(w,envelope,obstacles,plans)


@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=1,memory=4096,timeout=3600,
    max_containers=1,retries=0,volumes=mounts)
async def train():
    from collections import defaultdict
    import hashlib
    import numpy as np
    import tinker
    from tinker_cookbook import renderers,model_info
    from tinker_cookbook.recipes.decisions import DecisionRenderer,decision_choice_datums,sample_decision
    from mochi.navigation_tasks_v24.policy import decision
    from mochi.navigation_v23.services import NavigationServices
    from mochi.integrations import digest,now
    await volume.reload.aio()
    directory=Path('/artifacts')/RUN;out=directory/'task-training.json'
    assert not out.exists(),'Preserve completed and interrupted optimizer campaigns'
    data=json.loads((directory/'task-data.json').read_text())
    assert data['final_opened'] is False
    report={'run_id':RUN,'status':'running','phase':'task evidence handoff','optimizer_updates_completed':0,
        'checkpoints':[],'training_log':[],'data_sha256':digest(data),'charge_ordinal':0,
        'native_gait_weights_trained':False,'domain':'Contact and arm-recovery selection; separate adapter from the navigation selector.'}
    broker=modal.Function.from_name('mochi-continuation-v25','budget')
    async def charge(name,value):
        report['charge_ordinal']+=1
        report['usage_actual_or_reserved']=await broker.remote.aio(RUN,'task-training-service-'+str(report['charge_ordinal']),{name:value})
    services=NavigationServices(RUN+'-task',directory/'task-memory',charge,volume.commit.aio)
    async def save(name,value):
        p=directory/(name+'.json');p.write_text(json.dumps(value,indent=2)+'\n');await volume.commit.aio()
    async def publish():
        report['services']=services.report();await save('task-training',report)
        print(json.dumps({'phase':report['phase'],'updates':report['optimizer_updates_completed'],'status':report['status']}),flush=True)
    try:
        await publish();await services.setup()
        fact=await services.write('experimenter',{'kind':'task-controller-observation','source_sha256':data['engineering_sha256'],
            'observation':'A globe approach originally missed the frozen 4.5 mm sole-clearance requirement. An east-facing approach with contact-gated sole feedback qualified, and slower book-descent support transfer passed both matched seed probes. Three uninterrupted development runs now qualified, including the separate task-development arrangement. These are shared engineering results; task labels must come from measured component alternatives.'})
        await services.read('researcher',fact)
        search=await services.search('humanoid robot swing foot clearance residual controller post manipulation arm recovery smooth minimum jerk contact safety')
        hypothesis=await services.write('researcher',{'kind':'task-training-hypothesis','sources':search['sources'],'evidence':fact,
            'hypothesis':'Task-conditioned recovery selection can preserve contact validity with less arm travel than always using the staged recovery. Evaluate reached states and uninterrupted fresh sequences.'})
        await services.read('designer',hypothesis)
        plan=await services.write('designer',{'kind':'task-training-plan','source':hypothesis,'method':'Measured valid teacher labels, balanced task domains, unchanged evaluation checks. No final outcomes become labels.'})
        await services.read('experimenter',plan)
        service=tinker.ServiceClient(display_name=RUN+'-task-training')
        old=json.loads(Path('/previous/private-checkpoint-paths.json').read_text())
        trainer=await service.create_training_client_from_state(old['4']['optimizer'])
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),trainer.get_tokenizer()))
        groups=defaultdict(list)
        for record in data['training']:
            if record['target']:
                groups[record['domain']].extend(decision_choice_datums(renderer,[(decision(record['observation']),record['target'])]))
        assert set(groups)=={'alarm','drawer','laptop','globe','recovery'}
        rng=np.random.default_rng(252511)
        paths={};samplers={}
        async def checkpoint(update):
            state=await trainer.save_state(RUN.replace('-','_')+'_task_'+str(update))
            paths[str(update)]={'optimizer':state.path};await save('private-task-paths',paths)
            sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot');samplers[update]=sampler
            cp={'domain':'task and recovery','update':update,'checkpoint_id':digest(state.path),'at':now(),'development_choices':[]}
            for record in data['development']:
                rendered=renderer.render(decision(record['observation']));tokens=len(rendered.tokens)+1
                await charge('inference_input_plus_max_output_tokens',tokens);await charge('modeled_provider_usd',tokens*1.01/1e6)
                distribution=await sample_decision(sampler,rendered);action=max(distribution,key=distribution.get)
                measured=next(r for r in record['outcomes'] if r['action']==action)
                cp['development_choices'].append({'domain':record['domain'],'task':record['task'],'action':action,
                    'distribution':distribution,'valid':measured['valid'],'rank':measured['rank'],
                    'snapshot_sha256':record['snapshot_sha256'],'scope':'Matched-state component outcome lookup; not a continuous checkpoint rollout.'})
            choices=cp['development_choices'];cp['valid_components']=sum(c['valid'] for c in choices)
            cp['recovery_arm_travel_rad']=sum(c['rank'][0] for c in choices if c['domain']=='recovery' and c['valid'])
            cp['task_seconds']=sum(c['rank'][0] for c in choices if c['domain']!='recovery' and c['valid'])
            report['checkpoints'].append(cp);report['phase']='task checkpoint '+str(update);await publish()
        await checkpoint(0)
        for update in range(1,17):
            batch=[]
            domains=sorted(groups)
            for j in range(10):
                values=groups[domains[j%len(domains)]];batch.append(values[int(rng.integers(len(values)))])
            tokens=sum(d.model_input.length for d in batch)
            await charge('training_token_presentations',tokens);await charge('modeled_provider_usd',tokens*.737/1e6);await charge('optimizer_updates',1)
            backward=trainer.forward_backward(batch,loss_fn='cross_entropy');optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=1e-4))
            loss=await backward;await optimizer
            report['optimizer_updates_completed']=update
            report['training_log'].append({'update':update,'tokens':tokens,'forward_backward_completed':True,'optimizer_completed':True,'metrics':loss.metrics,'rng_state':rng.bit_generator.state,'at':now()})
            await publish()
            if update in [4,8,16]:await checkpoint(update)
        selected=max(report['checkpoints'],key=lambda cp:(cp['valid_components'],-cp['recovery_arm_travel_rad'],-cp['task_seconds'],-cp['update']))
        report['component_selected_checkpoint']=selected
        await save('task-component-selection',{'at':now(),'provisional_checkpoint':selected,'data_sha256':report['data_sha256'],
            'final_set_sha256':data['final_set_sha256'],'source_sha256':data['engineering_sha256'],'final_opened':False,
            'final_selection':False,'required_next_step':'Matched continuous development rollouts at all four checkpoints.'})
        finding=await services.write('experimenter',{'kind':'task-development-results','updates':16,'checkpoints':[{k:cp[k] for k in ['update','valid_components','recovery_arm_travel_rad','task_seconds']} for cp in report['checkpoints']],
            'qualification':'Matched-state development selection only. Fresh uninterrupted sequences are still required.'})
        await services.read('critic',finding)
        verdict=await services.write('critic',{'kind':'task-qualified-selection','evidence':finding,'selected_update':selected['update'],
            'conclusion':'Component selection is provisional. Compare all saved checkpoints on the same continuous development layout, then freeze the final selection. Component lookup does not establish end-to-end improvement.'})
        await services.read('researcher',verdict)
        report.update(status='completed',phase='Task weights saved; continuous development selection pending');await publish()
        return {'status':'completed','selected_update':selected['update'],'updates':16}
    except BaseException as error:
        report.update(status='incomplete',error_type=type(error).__name__);await publish();raise
    finally:await services.http.aclose()


@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=1,memory=4096,timeout=600,
    max_containers=1,retries=0,volumes=mounts)
async def choose(kind,update,observed,ident):
    import time
    import tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import DecisionRenderer,sample_decision
    from mochi.integrations import digest
    global _mochi_inference_cache
    if '_mochi_inference_cache' not in globals():_mochi_inference_cache={}
    assert kind in ['navigation','task'] and ident.replace('-','').isalnum()
    await volume.reload.aio()
    directory=Path('/artifacts')/RUN
    receipts=directory/'sequence-inferences';receipts.mkdir(exist_ok=True)
    target=receipts/(ident+'.json')
    request=digest([kind,update,observed])
    if target.exists():
        value=json.loads(target.read_text());assert value['request_sha256']==request;return value
    path=json.loads((directory/('private-navigation-paths.json' if kind=='navigation' else 'private-task-paths.json')).read_text())[str(update)]['optimizer']
    key=digest(path)
    if key not in _mochi_inference_cache:
        service=tinker.ServiceClient(display_name=RUN+'-sequence-inference')
        trainer=await service.create_training_client_from_state(path)
        sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot')
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),trainer.get_tokenizer()))
        _mochi_inference_cache[key]=(sampler,renderer)
    sampler,renderer=_mochi_inference_cache[key]
    if kind=='navigation':from mochi.navigation_v25.engine import decision
    else:from mochi.navigation_tasks_v24.policy import decision
    rendered=renderer.render(decision(observed));tokens=len(rendered.tokens)+1
    broker=modal.Function.from_name('mochi-continuation-v25','budget')
    await broker.remote.aio(RUN,'sequence-inference-'+ident,{'inference_input_plus_max_output_tokens':tokens,'modeled_provider_usd':tokens*1.01/1e6})
    start=time.perf_counter();distribution=await sample_decision(sampler,rendered)
    allowed=[a for a in distribution if kind!='navigation' or observed['options'][a]['feasible']]
    assert allowed,'No geometrically feasible model action'
    raw_choice=max(distribution,key=distribution.get)
    selected=max(allowed,key=distribution.get)
    value={'action':selected,'distribution':distribution,'checkpoint_id':key,'optimizer_updates':update,
        'source':'Actual Tinker checkpoint sampling; native gait fixed','kind':kind,'request_sha256':request,
        'observation_sha256':digest(observed),'inference_seconds':time.perf_counter()-start,'input_plus_reserved_output_tokens':tokens,
        'geometrically_available_actions':allowed,'raw_preference':raw_choice,'geometric_mask_changed_choice':raw_choice!=selected,
        'single_feasible_profile':len(allowed)==1}
    target.write_text(json.dumps(value,indent=2)+'\n');await volume.commit.aio()
    return value
