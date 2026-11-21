"""A bounded continuation: compact two-profile decisions, unchanged physics."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,existing_secrets,RUN

app=modal.App('mochi-navigation-v25-compact-training')

@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=1,memory=4096,timeout=14400,
    max_containers=1,retries=0,volumes={'/artifacts':volume})
async def train():
    import asyncio
    import copy
    from collections import defaultdict
    import hashlib
    import time
    import numpy as np
    import tinker
    from tinker_cookbook import renderers,model_info
    from tinker_cookbook.recipes.decisions import DecisionRenderer,decision_choice_datums,sample_decision
    from mochi.integrations import digest,now
    from mochi.navigation_v25.compact import ACTIONS,decision
    from mochi.navigation_v25.compact_baselines import contextual
    from mochi.navigation_v25.baselines import comparison
    from mochi.navigation_v23.baselines import summary
    from mochi.navigation_v23.layouts import fingerprint
    from mochi.navigation_v23.services import NavigationServices
    await volume.reload.aio()
    parent=Path('/artifacts')/RUN;directory=parent/'compact';target=directory/'navigation-training.json'
    assert not target.exists(),'Never overwrite a started optimizer campaign'
    assert json.loads((parent/'navigation-training.json').read_text())['optimizer_updates_completed']==32
    cfg=json.loads(Path('/app/configs/continuation-v25/compact/protocol.json').read_text())
    for name,h in json.loads(Path('/app/configs/continuation-v25/nav-source-freeze.json').read_text())['sha256'].items():
        assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==h,name
    data=json.loads((directory/'data.json').read_text());assert not data['final_opened']
    original_paths=json.loads((parent/'private-navigation-paths.json').read_text())
    paths={u:original_paths[u] for u in ['0','32']}
    report={'run_id':cfg['id'],'status':'running','phase':'compact evidence handoff','optimizer_updates_completed':0,
        'total_navigation_optimizer_updates':32,'checkpoints':[],'training_log':[],'development':{},'final':{},'final_opened':False,
        'protocol':cfg,'data_sha256':digest(data),'charge_ordinal':0,'native_gait_weights_trained':False,
        'baselines':data['baselines'],'scope':'Two-profile compact selector. New weight updates and representation changes are assessed separately.'}
    broker=modal.Function.from_name('mochi-continuation-v25','budget');trial=modal.Function.from_name('mochi-continuation-v25','trial')
    async def charge(kind,amount):
        report['charge_ordinal']+=1
        report['usage_actual_or_reserved']=await broker.remote.aio(RUN,'compact-service-'+str(report['charge_ordinal']),{kind:amount})
    async def save(name,value):
        p=directory/(name+'.json');p.write_text(json.dumps(value,indent=2)+'\n');await volume.commit.aio()
    services=NavigationServices(RUN+'-compact',directory/'memory',charge,volume.commit.aio)
    async def publish():
        report['services']=services.report();await save('navigation-training',report)
        print(json.dumps({k:report[k] for k in ['status','phase','optimizer_updates_completed','final_opened']}),flush=True)
    try:
        await publish();await services.setup()
        canary=await services.write('critic',{'kind':'synthetic-private-canary','value':'MOCHI_PRIVATE_CANARY_COMPACT'},private=True)
        await services.read('researcher',canary,allowed=False)
        observed=await services.write('experimenter',{'kind':'measured-clearance-failure','raw_campaign_updates':32,
            'finding':'Raw checkpoints 8 and 16 fail fixed-qualified development cases. A new physical checkpoint-32 diagnostic selects direct and misses sole clearance on a fixed-qualified reset.',
            'training_audit':'Raw update 32 agrees with 19/24 measured teachers but misses the sole buffered target. No final layout was opened.',
            'artifacts':['critical-development-u32.json','training-action-audit-u32.json']})
        await services.read('researcher',observed)
        search=await services.search('robot imitation learning compact state representation safety critical rare failure examples balanced behavior cloning')
        hypothesis=await services.write('researcher',{'kind':'compact-selector-hypothesis','sources':search['sources'],'prior_observation':observed,
            'mechanism':'Remove redundant raw geometry from the language-model prompt while retaining planner clearance and turn summaries; learn two measured speed/clearance alternatives.',
            'caveat':'The representation may help the parent too. Compare identical compact inputs before and after new weight updates.'})
        recalled=await services.read('designer',hypothesis)
        allocation=await services.decide('designer','Choose replay within each of two equally represented measured winner classes. Final layouts remain unopened.',recalled,
            ['balanced_compact','balanced_safety_weighted_compact'],[hypothesis])
        plan=await services.write('designer',{'kind':'compact-training-plan','allocation':allocation,'source':hypothesis,
            'training_layouts':32,'new_updates':16,'global_checkpoints':[0,32,40,48],
            'development':'Exact-trajectory-audited action lookup; full fresh final execution is required.'})
        await services.read('experimenter',plan)
        service=tinker.ServiceClient(display_name=cfg['id'])
        trainer=await service.create_training_client_from_state_with_optimizer(paths['32']['optimizer'])
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),trainer.get_tokenizer()))
        original=await service.create_training_client_from_state(paths['0']['optimizer'])
        samplers={0:await original.save_weights_and_get_sampling_client(kind='snapshot'),
            32:await trainer.save_weights_and_get_sampling_client(kind='snapshot')}
        await save('private-navigation-paths',paths)
        groups=defaultdict(list)
        for record in data['records']:
            if record['target']:
                for obs in record['observations']:
                    groups[record['target']].append((decision_choice_datums(renderer,[(decision(obs),record['target'])])[0],record))
        assert set(groups)==set(ACTIONS)
        async def pick(update,obs):
            rendered=renderer.render(decision(obs));tokens=len(rendered.tokens)+1
            await charge('inference_input_plus_max_output_tokens',tokens);await charge('modeled_provider_usd',tokens*1.01/1e6)
            start=time.perf_counter();distribution=await sample_decision(samplers[update],rendered)
            allowed=[a for a in ACTIONS if obs['options'][a]['feasible']]
            selected=max(allowed,key=distribution.get) if allowed else 'buffered'
            return {'action':selected,'distribution':distribution,'checkpoint_id':digest(paths[str(update)]['optimizer']),
                'optimizer_updates':update,'observation_sha256':digest(obs),'representation':'compact_two_profile',
                'inference_seconds':time.perf_counter()-start,'geometric_mask_changed_choice':selected!=max(distribution,key=distribution.get),
                'source':'Actual compact Tinker checkpoint; fixed native gait'}
        async def checkpoint(update):
            if update not in [0,32]:
                state=await trainer.save_state(RUN.replace('-','_')+'_compact_'+str(update))
                paths[str(update)]={'optimizer':state.path};await save('private-navigation-paths',paths)
                samplers[update]=await trainer.save_weights_and_get_sampling_client(kind='snapshot')
            entry={'update':update,'checkpoint_id':digest(paths[str(update)]['optimizer']),'at':now(),'representation':'compact_two_profile'}
            report['checkpoints'].append(entry);report['phase']='compact development checkpoint '+str(update);await publish()
            rows=[]
            for case in data['development_table']:
                selected=await pick(update,case['observation'])
                row=copy.deepcopy(case['outcomes'][selected['action']])
                row['recorded_physical_selection']=row['selection'];row['selection']=selected
                row['evidence_mode']='Exact deterministic development action-table lookup; no new physical attempt.'
                rows.append(row)
            fixed=[case['outcomes'][data['baselines']['fixed']] for case in data['development_table']]
            report['development'][str(update)]={'summary':summary(rows),'against_fixed':comparison(fixed,rows),
                'physical_rollouts_in_this_checkpoint_evaluation':0,'evidence_mode':'Audited complete physical outcome table, one initial discrete decision.'}
            await save('development-u'+str(update),rows);await publish()
        await checkpoint(0);await checkpoint(32)
        rng=np.random.default_rng(cfg['seed'])
        for update in range(33,49):
            batch=[];identities=[]
            for j in range(cfg['batch']):
                label=ACTIONS[j%len(ACTIONS)];values=groups[label]
                weights=np.array([3. if any(not v['qualified'] for outcomes in r['outcomes'].values() for v in outcomes) else 1. for _,r in values])
                i=int(rng.choice(len(values),p=weights/weights.sum() if allocation=='balanced_safety_weighted_compact' else None))
                datum,record=values[i];batch.append(datum);identities.append([label,record['layout_sha256'],i])
            tokens=sum(d.model_input.length for d in batch)
            await charge('training_token_presentations',tokens);await charge('modeled_provider_usd',tokens*.737/1e6);await charge('optimizer_updates',1)
            backward=trainer.forward_backward(batch,loss_fn='cross_entropy');optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=cfg['learning_rate']))
            loss=await backward;await optimizer
            report['optimizer_updates_completed']=update-32;report['total_navigation_optimizer_updates']=update
            report['training_log'].append({'global_update':update,'new_update':update-32,'tokens':tokens,
                'batch_sha256':digest(identities),'forward_backward_completed':True,'optimizer_completed':True,'metrics':loss.metrics,
                'rng_state':rng.bit_generator.state,'at':now()});await publish()
            if update in [40,48]:await checkpoint(update)
        candidates=[u for u in ['32','40','48'] if report['development'][u]['against_fixed']['win']]
        if not candidates:
            report.update(status='development_goal_unmet',phase='Compact training did not meet the fixed-strategy gate; final layouts remain unopened')
            await publish();return {'status':report['status'],'new_updates':16}
        selected=min(candidates,key=lambda u:(report['development'][u]['against_fixed']['mean_layout_step_ratio'],int(u)))
        report['selected_checkpoint']=next(c for c in report['checkpoints'] if c['update']==int(selected))
        await save('selection-freeze',{'at':now(),'selected_checkpoint':report['selected_checkpoint'],'data_sha256':report['data_sha256'],
            'protocol':cfg,'final_set_sha256':data['final_set_sha256'],'final_opened':False,'native_gait_weights_trained':False})
        conclusion=await services.write('experimenter',{'kind':'compact-development-results','selected':report['selected_checkpoint'],
            'results':{k:v['against_fixed'] for k,v in report['development'].items()},
            'caveat':'Development outcomes are exact audited physical lookups. Fresh final physical episodes are still required.'})
        await services.read('critic',conclusion)
        verdict=await services.write('critic',{'kind':'compact-qualified-freeze','evidence':conclusion,
            'conclusion':'Freeze the selected compact weights. Evaluate every declared final layout without further tuning. Separate representation changes from incremental weight gains.'})
        await services.read('researcher',verdict)
        final=json.loads((parent/'sealed/final_navigation.json').read_text());assert fingerprint(final)==data['final_set_sha256']
        report.update(final_opened=True,phase='Fresh final navigation execution');await publish()
        slots=asyncio.Semaphore(3)
        async def cohort(label,update=None,baseline=None):
            async def one(i,layout,seed):
                async with slots:
                    from mochi.navigation_v25.engine import inspect,observation
                    w,e,o,p=inspect(layout,seed);obs=observation(w,e,o,p)
                    selection=await pick(update,obs) if update is not None else {}
                    action=selection['action'] if update is not None else contextual(obs,data['baselines']['contextual']) if baseline=='contextual' else baseline
                    ident=f'compact-final-{label}-{i}-{seed}'
                    await broker.remote.aio(RUN,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1,'modeled_provider_usd':.02})
                    row=await trial.remote.aio(layout,seed,action,selection,ident)
                    await broker.remote.aio(RUN,ident+'-actual',{'simulation_cpu_hours':row['receipt']['duration_seconds']/3600-.1})
                    return row
            rows=await asyncio.gather(*(one(i,l,s) for i,l in enumerate(final) for s in [251000,251001]))
            await save('final-'+label,rows);report['final'][label]=summary(rows);await publish();return rows
        # All policies run physically. Cohorts overlap only in scheduling.
        parent_rows,selected_rows,fixed_rows,contextual_rows=await asyncio.gather(cohort('parent',0),cohort('selected',int(selected)),
            cohort('fixed',baseline=data['baselines']['fixed']),cohort('contextual',baseline='contextual'))
        report['final_against_fixed']=comparison(fixed_rows,selected_rows)
        report['final_against_parent']=comparison(parent_rows,selected_rows)
        report['final_against_contextual']=comparison(contextual_rows,selected_rows)
        report.update(status='completed',phase='Compact navigation cohort completed');await publish()
        return {'status':'completed','new_updates':16,'selected_update':int(selected),'against_fixed':report['final_against_fixed']}
    except BaseException as error:
        report.update(status='incomplete',error_type=type(error).__name__);await publish();raise
    finally:await services.http.aclose()
