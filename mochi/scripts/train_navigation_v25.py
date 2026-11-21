"""Detached balanced post-training, development selection and unopened tests."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image, volume, existing_secrets, RUN

ROOT=Path(__file__).resolve().parents[1]
app=modal.App('mochi-navigation-v25-training')
previous=modal.Volume.from_name('mochi-navigation-v23-artifacts')


@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=1,memory=4096,
    timeout=21600,max_containers=1,retries=0,
    volumes={'/artifacts':volume,'/previous':previous.with_mount_options(read_only=True,sub_path='/mochi-nav23-20261121c')})
async def train(resume=False,recover_evaluation=False):
    import asyncio
    import copy
    from collections import Counter,defaultdict
    import hashlib
    import time
    import numpy as np
    import tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import DecisionRenderer,decision_choice_datums,sample_decision
    from mochi.integrations import now,digest
    from mochi.navigation_v25.engine import ACTIONS,inspect,observation,decision
    from mochi.navigation_v25.baselines import tune,contextual,comparison as numerical_comparison
    from mochi.navigation_v23.baselines import summary
    from mochi.navigation_v23.layouts import fingerprint
    from mochi.navigation_v23.services import NavigationServices
    def scalar(value):
        if isinstance(value,np.generic):return value.item()
        raise TypeError('Unexpected non-JSON value: '+type(value).__name__)
    def comparison(*args):return json.loads(json.dumps(numerical_comparison(*args),default=scalar))
    await volume.reload.aio()
    directory=Path('/artifacts')/RUN
    directory.mkdir(exist_ok=True)
    target=directory/'navigation-training.json'
    prior=json.loads(target.read_text()) if target.exists() else None
    if prior:
        if recover_evaluation:
            assert prior['optimizer_updates_completed']==32 and not prior['final_opened']
            assert [c['update'] for c in prior['checkpoints']]==[0,8,16,32]
        else:
            assert resume and prior['status']=='incomplete' and prior['optimizer_updates_completed']==0 and not prior['final_opened'] and not prior['checkpoints']
    else:
        assert not resume

    cfg=json.loads(Path('/app/configs/continuation-v25/protocol.json').read_text())
    split=json.loads(Path('/app/configs/continuation-v25/navigation-splits.json').read_text())
    report={'run_id':RUN,'status':'running','phase':'research handoff','at':now(),
        'optimizer_updates_completed':0,'training_log':[],'checkpoints':[],
        'development':{},'final':{},'final_opened':False,'native_gait_weights_trained':False,
        'protocol':cfg,'split_manifest':split,'charge_ordinal':0,'source_sha256':hashlib.sha256(Path('/app/configs/continuation-v25/nav-source-freeze.json').read_bytes()).hexdigest()}
    if prior:
        report=copy.deepcopy(prior)
        report.update(status='running',phase='Resume immutable collection after duplicate audit')
        report['recovery']={'at':now(),'optimizer_updates_repeated':0,'physical_source_changed':False,'scope':'Collection/cache recovery before the first optimizer update. Original failed reports and both physical attempts are archived.'}
        if recover_evaluation:
            report['recovery']={'at':now(),'optimizer_updates_repeated':0,'physical_source_changed':False,
                'scope':'Resume saved update-32 weights and optimizer after a NumPy-integer JSON reporting failure. All original snapshots, completed physical attempts, learning rules and selection criteria are preserved.'}
            report.pop('error_type',None)
    broker=modal.Function.from_name('mochi-continuation-v25','budget')
    trial=modal.Function.from_name('mochi-continuation-v25','trial')
    collector=modal.Function.from_name('mochi-navigation-v25-collection','collect')
    async def save(name,value):
        p=directory/(name+'.json');temp=p.with_suffix('.tmp')
        temp.write_text(json.dumps(value,indent=2,default=scalar)+'\n');temp.replace(p)
        await volume.commit.aio()
    async def charge(kind,amount):
        report['charge_ordinal']+=1
        usage=await broker.remote.aio(RUN,'training-service-'+str(report['charge_ordinal']),{kind:amount})
        report['usage_actual_or_reserved']=usage
    services=NavigationServices(RUN,directory,charge,volume.commit.aio)
    if recover_evaluation:
        ledger=await modal.Dict.from_name('mochi-continuation-v25-budget').get.aio(RUN)
        report['charge_ordinal']=max(int(k.rsplit('-',1)[1]) for k in ledger['transactions'] if k.startswith('training-service-'))
    if prior:
        journal=json.loads((directory/'memory-journal.json').read_text())
        for field in ['records','pending','reads','calls','sources','decisions']:setattr(services,field,journal[field])
        assert not services.pending

    publication_lock=asyncio.Lock()
    async def publish():
        async with publication_lock:
            report['services']=services.report();await save('navigation-training',report)
            print(json.dumps({'status':report['status'],'phase':report['phase'],'updates':report['optimizer_updates_completed'],
                'development_checkpoints':list(report['development']),'final_opened':report['final_opened']}),flush=True)
    paths,samplers,observations={},{},{}
    renderer=None
    async def observed(layout,seed):
        key=(layout['layout_sha256'],seed)
        if key not in observations:
            w,e,o,p=inspect(layout,seed);observations[key]=observation(w,e,o,p)
        return copy.deepcopy(observations[key])
    async def pick(update,obs):
        rendered=renderer.render(decision(obs));n=len(rendered.tokens)+1
        await charge('inference_input_plus_max_output_tokens',n)
        await charge('modeled_provider_usd',n*1.01/1_000_000)
        t=time.perf_counter();distribution=await sample_decision(samplers[update],rendered)
        return {'action':max(distribution,key=distribution.get),'distribution':distribution,
            'checkpoint_id':digest(paths[str(update)]['optimizer']),'optimizer_updates':update,
            'observation_sha256':digest(obs),'inference_seconds':time.perf_counter()-t,
            'source':'Actual Tinker navigation checkpoint; fixed native gait'}
    slots=asyncio.Semaphore(4)
    async def physical(layout,seed,action,selection,ident):
        cache=directory/'physics'/(ident+'.summary.json')
        if cache.exists():
            row=json.loads(cache.read_text());assert row['layout_sha256']==layout['layout_sha256'] and row['seed']==seed
            return row
        await broker.remote.aio(RUN,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1,'modeled_provider_usd':.02})
        row=await trial.remote.aio(layout,seed,action,selection,ident)
        await broker.remote.aio(RUN,ident+'-actual',{'simulation_cpu_hours':row['receipt']['duration_seconds']/3600-.1})
        return row
    async def evaluate(label,layouts,update=None,baseline=None):
        async def one(i,layout,seed):
            async with slots:
                ident=f'{label}-{i}-{seed}'
                cached=directory/'physics'/(ident+'.summary.json')
                if cached.exists():
                    row=json.loads(cached.read_text())
                    if update is not None:assert row['selection']['checkpoint_id']==digest(paths[str(update)]['optimizer'])
                    await broker.remote.aio(RUN,ident+'-actual',{'simulation_cpu_hours':row['receipt']['duration_seconds']/3600-.1})
                    return row
                obs=await observed(layout,seed)
                if update is None:
                    action=contextual(obs,baselines['contextual']) if baseline=='contextual' else baseline
                    selected={}
                else:
                    stored=directory/('prediction-'+ident+'.json')
                    if recover_evaluation and stored.exists():
                        selected=json.loads(stored.read_text())
                        assert selected['checkpoint_id']==digest(paths[str(update)]['optimizer'])
                    else:
                        selected=await pick(update,obs)
                        await save('prediction-'+ident,selected)
                    action=selected['action']
                return await physical(layout,seed,action,selected,ident)
        return await asyncio.gather(*(one(i,l,s) for i,l in enumerate(layouts) for s in [251000,251001]))
    try:
        if not resume and not recover_evaluation:
            await publish();await services.setup()
            private=await services.write('critic',{'kind':'private-canary','value':'MOCHI_PRIVATE_CANARY_'+RUN},private=True)
            await services.read('researcher',private,allowed=False)
            rid=await services.write('experimenter',{'kind':'observed-selector-collapse','experiment_id':RUN,
                'previous_study':'mochi-nav23-20261121c','training_targets':{'direct':14,'buffered':1},
                'selected_final_choices':{'direct':16},'selected_qualified':14,'fixed_qualified':16,
                'qualification':'Prior closed cohort supplies a diagnosis, not fresh-test evidence or labels for the new physical implementation.'})
            evidence=await services.read('researcher',rid)
            sources=await services.search('cost sensitive imitation learning class imbalance rare safety failures robot policy selection dataset balancing')
            sourced=await services.write('researcher',{'kind':'sourced-training-hypothesis','experiment_id':RUN,
                'prior_evidence':rid,'sources':sources,'mechanism':'Retain rare safe-controller choices by balancing measured winner classes and emphasizing observed failures.','test':'New source and layouts; compare identical frozen parent and updated weights with strong fixed controls.'})
            context=await services.read('designer',sourced)
            allocation=await services.decide('designer','Choose one balanced replay allocation. No final layout or outcome may enter training.',context,
                ['stratified_by_winner','safety_weighted_minibatches'],[sourced])
            plan=await services.write('designer',{'kind':'training-allocation','allocation':allocation,'evidence':sourced,
                'qualification':'Labels are produced only by real physical candidate outcomes across two seeds.'})
            await services.read('experimenter',plan)
            await publish()
        else:
            allocation=next(d['selected'] for d in services.decisions if d['role']=='designer')
            await publish()
        async def collection(count):
            name='training'+str(count);file=directory/('collection-'+name+'.json')
            report['phase']='measured candidate collection '+str(count);await publish()
            if not file.exists() or json.loads(file.read_text())['status']!='completed':await collector.remote.aio(count,name)
            await volume.reload.aio()
            data=json.loads(file.read_text());assert data['status']=='completed'
            return data
        data=await collection(24)
        if len([k for k,n in data['targets'].items() if k!='null' and n>=2])<2:
            data=await collection(32)
        labels=Counter(r['target'] for r in data['records'] if r['target'])
        report['training_targets']=dict(labels);report['training_data_sha256']=data['data_sha256']
        assert len(labels)>=2,'No conditional learning target: one fixed strategy dominates the measured training data'
        baselines=tune(data['records']);report['baselines']=baselines
        developmental=json.loads(Path('/app/configs/continuation-v25/development.json').read_text())
        report['phase']='development controls';await publish()
        controls={}
        async def control(label,action):
            controls[label]=await evaluate('dev-'+label,developmental,baseline=action)
            await save('development-'+label,controls[label]);await publish()
        control_jobs=[asyncio.create_task(control(label,action)) for label,action in
            [('fixed',baselines['fixed']),('planner','planner'),('contextual','contextual')]]
        checkpoint_jobs=[]
        services.service=tinker.ServiceClient(display_name=RUN+'-balanced-navigation')
        previous_paths=json.loads(Path('/previous/private-checkpoint-paths.json').read_text())
        if recover_evaluation:
            paths.update(json.loads((directory/'private-navigation-paths.json').read_text()))
            trainer=await services.service.create_training_client_from_state_with_optimizer(paths['32']['optimizer'])
        else:trainer=await services.service.create_training_client_from_state(previous_paths['4']['optimizer'])
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(cfg['model']),trainer.get_tokenizer()))
        report['parent_origin']={'previous_update':4,'checkpoint_id':digest(previous_paths['4']['optimizer']),
            'optimizer':'Fresh Adam state for the balanced curriculum; exact parent weights restored.'}
        groups=defaultdict(list)
        for record in data['records']:
            if record['target']:
                for obs in record['observations']:
                    datum=decision_choice_datums(renderer,[(decision(obs),record['target'])])[0]
                    groups[record['target']].append((datum,record))
        probe=data['records'][0]['observations'][0]
        async def evaluate_snapshot(update):
            rows=await evaluate('dev-u'+str(update),developmental,update=update)
            await control_jobs[0]
            report['development'][str(update)]={'summary':summary(rows),'against_fixed':comparison(controls['fixed'],rows)}
            await save('development-u'+str(update),rows);await publish()
        async def checkpoint(update):
            saved=await trainer.save_state(RUN.replace('-','_')+'_navigation_'+str(update))
            paths[str(update)]={'optimizer':saved.path};await save('private-navigation-paths',paths)
            samplers[update]=await trainer.save_weights_and_get_sampling_client(kind='snapshot')
            entry={'update':update,'checkpoint_id':digest(saved.path),'at':now()}
            report['checkpoints'].append(entry);report['phase']='fixed development checkpoint '+str(update);await publish()
            entry['probe_distribution']=(await pick(update,probe))['distribution']
            # Sampling uses an immutable snapshot. Weight updates can continue
            # while these fixed-cohort physical evaluations wait in the queue.
            checkpoint_jobs.append(asyncio.create_task(evaluate_snapshot(update)))
        if recover_evaluation:
            for entry in report['checkpoints']:
                update=entry['update']
                client=trainer if update==32 else await services.service.create_training_client_from_state(paths[str(update)]['optimizer'])
                samplers[update]=await client.save_weights_and_get_sampling_client(kind='snapshot')
                if 'probe_distribution' not in entry:entry['probe_distribution']=(await pick(update,probe))['distribution']
                checkpoint_jobs.append(asyncio.create_task(evaluate_snapshot(update)))
        else:await checkpoint(0)
        parent_probe=report['checkpoints'][0]['probe_distribution']
        rng=np.random.default_rng(251411)
        if recover_evaluation:
            # Replay only the deterministic minibatch index draws, not gradients.
            classes=sorted(groups)
            for _ in range(32):
                for j in range(12):
                    values=groups[classes[j%len(classes)]]
                    weights=np.array([3. if any(not v['qualified'] for outcomes in r['outcomes'].values() for v in outcomes) else 1. for _,r in values])
                    rng.choice(len(values),p=weights/weights.sum() if allocation=='safety_weighted_minibatches' else None)
        async def update_weights(update):
            batch=[];identities=[]
            classes=sorted(groups)
            for j in range(12):
                action=classes[j%len(classes)];values=groups[action]
                weights=np.array([3. if any(not v['qualified'] for outcomes in r['outcomes'].values() for v in outcomes) else 1. for _,r in values])
                probabilities=weights/weights.sum() if allocation=='safety_weighted_minibatches' else None
                i=int(rng.choice(len(values),p=probabilities));datum,record=values[i]
                batch.append(datum);identities.append([action,record['layout_sha256'],i])
            tokens=sum(d.model_input.length for d in batch)
            await charge('training_token_presentations',tokens);await charge('modeled_provider_usd',tokens*.737/1_000_000)
            await charge('optimizer_updates',1)
            backward=trainer.forward_backward(batch,loss_fn='cross_entropy')
            optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=5e-5))
            loss=await backward;await optimizer
            report['optimizer_updates_completed']=update
            report['training_log'].append({'update':update,'tokens':tokens,'batch_sha256':digest(identities),
                'forward_backward_completed':True,'optimizer_completed':True,'metrics':loss.metrics,'at':now()})
            await publish()
        for update in range(33 if recover_evaluation else 1,33):
            report['phase']='balanced Tinker optimizer update '+str(update)
            await update_weights(update)
            if update in [8,16,32]:await checkpoint(update)
        await asyncio.gather(*control_jobs,*checkpoint_jobs)
        if not any(v['against_fixed']['win'] for k,v in report['development'].items() if k!='0'):
            report['phase']='extend training with fresh training layouts';await publish()
            extra=await collection(32)
            # Add newly measured examples; no development outcome becomes a label.
            for record in extra['records'][len(data['records']):]:
                if record['target']:
                    for obs in record['observations']:
                        groups[record['target']].append((decision_choice_datums(renderer,[(decision(obs),record['target'])])[0],record))
            data=extra;report['training_targets']=dict(Counter(r['target'] for r in data['records'] if r['target']))
            report['training_data_sha256']=data['data_sha256']
            for update in range(33,49):
                await update_weights(update)
            await checkpoint(48)
            await asyncio.gather(*checkpoint_jobs)
        report['maximum_probe_change']=max(abs(c['probe_distribution'][a]-parent_probe[a]) for c in report['checkpoints'] for a in ACTIONS)
        assert report['maximum_probe_change']>1e-7,'No changed decision probabilities after optimizer updates'
        candidates=[u for u,v in report['development'].items() if u!='0' and v['against_fixed']['win']]
        if not candidates:
            report.update(status='development_goal_unmet',phase='Fresh final layouts remain unopened')
            await publish();return {'status':report['status'],'updates':report['optimizer_updates_completed']}
        selected=min(candidates,key=lambda u:(report['development'][u]['against_fixed']['mean_layout_step_ratio'],int(u)))
        report['selected_checkpoint']=next(c for c in report['checkpoints'] if c['update']==int(selected))
        selection={'at':now(),'selected_checkpoint':report['selected_checkpoint'],'source_sha256':report['source_sha256'],
            'split_manifest':split,'training_data_sha256':report['training_data_sha256'],'baselines':baselines,
            'native_gait_weights_trained':False}
        await save('selection-freeze',selection)
        record=await services.write('experimenter',{'kind':'development-results','selected':report['selected_checkpoint'],
            'controls':{k:summary(v) for k,v in controls.items()},'checkpoints':report['development'],
            'qualification':'Final layouts have not been evaluated. Selection follows the frozen qualification and paired-efficiency gate.'})
        context=await services.read('critic',record)
        verdict=await services.write('critic',{'kind':'development-qualification','evidence':record,
            'decision':'Evaluate the frozen selected checkpoint once on the unopened cohort. No subsequent tuning on it.'})
        await services.read('researcher',verdict)
        final=json.loads((directory/'sealed/final_navigation.json').read_text())
        assert fingerprint(final)==split['final_navigation']['sha256']
        report['final_opened']=True;report['phase']='unopened final navigation evaluation';await publish()
        for label,update,baseline in [('parent',0,None),('selected',int(selected),None),('fixed',None,baselines['fixed']),('contextual',None,'contextual')]:
            rows=await evaluate('final-'+label,final,update=update,baseline=baseline)
            await save('final-'+label,rows);report['final'][label]=summary(rows);await publish()
        selected_rows=json.loads((directory/'final-selected.json').read_text());fixed_rows=json.loads((directory/'final-fixed.json').read_text())
        report['final_against_fixed']=comparison(fixed_rows,selected_rows)
        evidence=await services.write('experimenter',{'kind':'final-navigation-results','summaries':report['final'],
            'against_fixed':report['final_against_fixed'],'qualification':'Eight fresh layouts, two seeds; fixed native gait. Source and weights frozen before the first final attempt.'})
        await services.read('critic',evidence)
        conclusion=await services.write('critic',{'kind':'final-qualified-conclusion','evidence':evidence,
            'goal_met':report['final_against_fixed']['win'],'qualification':'Counts and paired uncertainty determine the claim. No future layout generalization or native gait learning is established by this cohort.'})
        await services.read('researcher',conclusion)
        report.update(status='completed',phase='navigation complete')
        await publish()
        return {'status':'completed','updates':report['optimizer_updates_completed'],'against_fixed':report['final_against_fixed']}
    except BaseException as error:
        report.update(status='incomplete',error_type=type(error).__name__)
        await publish();raise
    finally:
        await services.http.aclose()


@app.local_entrypoint()
def launch(resume:bool=False):
    p=ROOT/'artifacts/continuation-v25'/('training-resume-r1-launch.json' if resume else 'training-launch.json')
    assert not p.exists()
    call=modal.Function.from_name('mochi-navigation-v25-training','train').spawn(resume)
    p.write_text(json.dumps({'run_id':RUN,'call_id':call.object_id,'detached':True},indent=2)+'\n')
    print(json.dumps({'run':RUN,'call_id':call.object_id,'detached':True}))
