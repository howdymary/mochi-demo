"""Continuous development selection, followed by a single sealed task cohort."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import modal
from mochi.navigation_v23.layouts import fingerprint

root=Path(__file__).resolve().parents[1]
directory=root/'artifacts/continuation-v25'
config=root/'configs/continuation-v25/tasks'
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','final'],required=True)
p.add_argument('--allow-fixed-navigation',action='store_true')
p.add_argument('--engineering-revision',choices=['r2','r3','r5'],default='r2')
p.add_argument('--workers',type=int,default=2)
p.add_argument('--fixed-navigation-study',action='store_true');args=p.parse_args()
assert 1<=args.workers<=5
run=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id']
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
def remote(name):return json.loads(b''.join(volume.read_file(run+'/'+name+'.json')))
def save(name,value):
    target=directory/(name+'.json');assert not target.exists();target.write_text(json.dumps(value,indent=2)+'\n')
    with volume.batch_upload() as batch:batch.put_file(target,'/'+run+'/'+name+'.json')
report=remote('task-training');assert report['status']=='completed' and report['optimizer_updates_completed']==16
frozen=config/f'physical-freeze-{args.engineering_revision}.json'
for name,expected in json.loads(frozen.read_text())['sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
jobs=[]
if args.phase=='development':
    layout=config/'development.json'
    for update in [0,4,8,16]:
        jobs.append({'id':'task-dev-u'+str(update),'update':update,'seed':252000,'layout':layout,
            'settings':{'navigation':{'mode':'fixed','action':'buffered'},'task':{'update':update}}})
else:
    selected=json.loads((directory/'task-selection-freeze.json').read_text())
    assert selected['qualified_complete']
    try:
        navigation=remote('compact/navigation-training');compact=True
    except (modal.exception.NotFoundError,FileNotFoundError):
        navigation=remote('navigation-training');compact=False
    assert navigation['status'] in ['completed','development_goal_unmet'] or (navigation.get('selected_checkpoint') and navigation['final_opened']),'Wait for navigation selection to be frozen'
    nav_update=navigation['selected_checkpoint']['update'] if navigation.get('selected_checkpoint') else None
    if args.fixed_navigation_study:
        assert args.engineering_revision=='r2'
        assert (config/'fixed-navigation-task-study-amendment.json').exists()
        nav_update=None
    if nav_update is None and not args.allow_fixed_navigation:
        raise RuntimeError('Navigation selection has not passed its gate; preserve unopened final task layouts while navigation work continues')
    prepared=modal.Function.from_name('mochi-task-control-v25','prepare_serving').remote(nav_update,selected['selected_update'],compact)
    preparation=directory/'serving-preparation.json'
    if not preparation.exists():preparation.write_text(json.dumps(prepared,indent=2)+'\n')
    # The task adapter was selected with a fixed navigation wrapper. Validate
    # the newly combined navigation/task models before opening any final task layout.
    def integration(side):
        update=0 if side=='parent' else selected['selected_update']
        nav={'mode':'tinker','update':0 if side=='parent' else nav_update} if nav_update is not None else {'mode':'fixed','action':'buffered'}
        if compact and nav_update is not None:nav['representation']='compact'
        settings={'navigation':nav,'task':{'update':update}}
        if nav_update is None:
            existing=json.loads((directory/f'task-dev-u{update}.metadata.json').read_text())
            assert existing['policy_settings']==settings
            return dict(existing,integration_evidence='Identical already-executed fixed-navigation development configuration; no new episode.')
        revision_prefix='' if args.engineering_revision=='r2' else args.engineering_revision+'-'
        ident='task-integration-'+revision_prefix+('local-' if args.engineering_revision=='r5' else '')+side
        policy=directory/(ident+'-policy.json');raw=json.dumps(settings,indent=2)+'\n'
        if policy.exists():assert policy.read_text()==raw
        else:policy.write_text(raw)
        metadata=directory/(ident+'.metadata.json')
        if not metadata.exists():
            with (directory/(ident+'.log')).open('w') as log:
                command=[sys.executable,str(root/'scripts/probe_sequence_v25.py'),'--id',ident,'--seed','252000',
                    '--layout',str(config/'development.json'),'--policy-config',str(policy),
                    '--engineering-revision',args.engineering_revision]
                completed=subprocess.run(command,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT)
            assert completed.returncode==0,(ident,'Inspect retained incomplete integration attempt')
        row=json.loads(metadata.read_text())
        print(json.dumps({'integration':side,'qualified':row.get('qualified_complete'),'steps':row.get('steps')}),flush=True)
        return row
    integration_name='task-integration-'+('fixed-navigation-' if args.fixed_navigation_study else '')+('' if args.engineering_revision=='r2' else args.engineering_revision+'-')+('local-' if args.engineering_revision=='r5' else '')+'continuous'
    integration_file=directory/(integration_name+'.json')
    if not integration_file.exists():
        with ThreadPoolExecutor(max_workers=2) as pool:integrated=list(pool.map(integration,['parent','selected']))
        save(integration_name,{'results':integrated,'selected_qualified':integrated[1].get('qualified_complete',False),
            'engineering_revision':args.engineering_revision,'physical_source_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),
            'scope':'Combined frozen models on development geometry, before opening final task layouts. No checkpoint tuning uses final outcomes.'})
    assert json.loads(integration_file.read_text())['selected_qualified'],'Combined development sequence failed; final task layouts remain unopened'
    if args.workers>2:
        assert navigation['status']=='completed','Five task workers require navigation to have ended'
        stopped=json.loads((directory/'task-remote-r5-stop.json').read_text())
        assert stopped['status']=='stopped' and stopped['app_id']=='ap-8ifaPG5AzCWumEJXvM5LA8','Preserve the global physical-worker ceiling'
        assert (config/'local-runtime-r5-amendment.json').exists()
    sealed=directory/'sealed/final_tasks.json';layouts=json.loads(sealed.read_text())
    splits=json.loads((config/'splits.json').read_text())
    assert fingerprint(layouts)==splits['final']['sha256']
    marker=directory/'task-final-opened.json'
    if not marker.exists():save('task-final-opened',{'selection_sha256':fingerprint(selected),'set_sha256':fingerprint(layouts),
        'navigation_selected_update':nav_update,'task_selected_update':selected['selected_update'],
        'engineering_revision':args.engineering_revision,'physical_source_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),
        'runtime':'local single-thread arm64; identical for both model sides',
        'study_scope':'Task/recovery weight comparison with the same training-selected fixed navigation wrapper.' if args.fixed_navigation_study else 'Combined learned navigation and task models.',
        'qualification':'Final outcomes cannot become training labels. All declared layouts and both seeds are included.'})
    for i,layout in enumerate(layouts):
        path=directory/('task-final-layout-'+str(i)+'.json')
        raw=json.dumps(layout,indent=2)+'\n'
        if path.exists():assert path.read_text()==raw
        else:path.write_text(raw)
        for seed in splits['final']['physics_seeds']:
            for side,update in [('parent',0),('selected',selected['selected_update'])]:
                nav={'mode':'tinker','update':0 if side=='parent' else nav_update} if nav_update is not None else {'mode':'fixed','action':'buffered'}
                if compact and nav_update is not None:nav['representation']='compact'
                jobs.append({'id':f'task-final-{i}-{seed}-{side}','update':update,'seed':seed,'layout':path,
                    'settings':{'navigation':nav,'task':{'update':update}}})

def attempt(job):
    ident=job['id'];metadata=directory/(ident+'.metadata.json');policy=directory/(ident+'-policy.json')
    raw=json.dumps(job['settings'],indent=2)+'\n'
    if policy.exists():assert policy.read_text()==raw
    else:policy.write_text(raw)
    if not metadata.exists():
        command=[sys.executable,str(root/'scripts/probe_sequence_v25.py'),'--id',ident,'--seed',str(job['seed']),
            '--layout',str(job['layout']),'--policy-config',str(policy),'--engineering-revision',args.engineering_revision]
        with (directory/(ident+'.log')).open('w') as log:
            completed=subprocess.run(command,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT)
        assert completed.returncode==0,(ident,'Inspect retained log and interrupted attempt; do not overwrite')
    result=json.loads(metadata.read_text());assert result.get('status')!='incomplete',ident
    result['task_checkpoint_update']=job['update']
    print(json.dumps({k:result[k] for k in ['id','qualified_complete','steps','physical_seconds','task_checkpoint_update']}),flush=True)
    return result

with ThreadPoolExecutor(max_workers=args.workers) as pool:results=list(pool.map(attempt,jobs))
save('task-'+args.phase+'-continuous',{'phase':args.phase,'results':results,'physical_source_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),
    'engineering_revision':args.engineering_revision,
    'runtime':'local single-thread arm64; identical for both model sides',
    'fixed_navigation':args.fixed_navigation_study,
    'scope':f'Each row is one uninterrupted physical rollout from reset. At most {args.workers} local CPU workers; no branch splicing. Matched source, layout, reset and playback time.'})
if args.phase=='development':
    qualified=[r for r in results if r['qualified_complete']]
    if not qualified:
        print(json.dumps({'status':'development_goal_unmet','final_opened':False}));sys.exit(0)
    def rank(row):
        import gzip
        episode=json.loads(gzip.decompress((directory/(row['id']+'.json.gz')).read_bytes()))['episode']
        travel=sum(r['arm_joint_travel_rad'] for r in episode['recoveries'])
        row['recovery_arm_travel_rad']=travel
        return row['steps'],travel,row['physical_seconds'],row['task_checkpoint_update']
    winner=min(qualified,key=rank)
    save('task-selection-freeze',{'selected_update':winner['task_checkpoint_update'],'qualified_complete':True,
        'selected_run':winner,'criterion':'Qualified complete sequence, steps, recovery arm travel, physical time, earlier update.',
        'final_opened':False,'final_set_sha256':json.loads((config/'splits.json').read_text())['final']['sha256'],
        'engineering_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest()})
    print(json.dumps({'selected_update':winner['task_checkpoint_update'],'final_opened':False}))
