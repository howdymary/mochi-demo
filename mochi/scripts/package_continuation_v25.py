"""Publish measured attempts and compact, non-secret provenance for the viewer."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

import modal

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--preview',action='store_true')
parser.add_argument('--compact',action='store_true')
args=parser.parse_args()
run=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id']
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
local=root/'artifacts/continuation-v25/cloud';local.mkdir(exist_ok=True)
web=root/'web/desk/continuation-v25';web.mkdir(exist_ok=True)
evidence=root/'evidence/continuation-v25';evidence.mkdir(exist_ok=True)


def download(name):
    raw=b''.join(volume.read_file(run+'/'+name))
    (local/name.replace('/','__')).write_bytes(raw)
    return json.loads(raw)


def sanitize(value):
    if isinstance(value,dict):
        return {k:sanitize(v) for k,v in value.items() if k not in ['returned_source_ids','private_canary','private_checkpoint_paths']}
    if isinstance(value,list):return [sanitize(v) for v in value]
    return value


prefix='compact/' if args.compact else ''
report=download(prefix+'navigation-training.json')
assert report['status'] in ['completed','development_goal_unmet'] or args.preview
assert report['optimizer_updates_completed']>0
is_final=report['status']=='completed' and report['final_opened']
selected=(report.get('selected_checkpoint') or report['checkpoints'][-1])['update']
rows={}
labels={'parent':'Parent · update 0','selected':f'Selected · update {selected}',
    'fixed':'Strongest fixed strategy','contextual':'Training-fitted contextual control','planner':'Collision-aware planner'}
if is_final:
    for name in ['parent','selected','fixed','contextual']:rows[name]=download(prefix+'final-'+name+'.json')
else:
    rows['parent']=download(prefix+'development-u0.json')
    for cp in report['checkpoints']:
        key='selected' if cp['update']==selected else 'u'+str(cp['update'])
        if cp['update']:
            rows[key]=download(prefix+'development-u'+str(cp['update'])+'.json')
            labels[key]=f'Checkpoint · update {cp["update"]}'
    if args.compact:
        table=download('compact/data.json')['development_table']
        fit=report['baselines']
        from mochi.navigation_v25.compact_baselines import contextual
        rows['fixed']=[c['outcomes'][fit['fixed']] for c in table]
        rows['contextual']=[c['outcomes'][contextual(c['observation'],fit['contextual'])] for c in table]
    else:
        for name in ['fixed','contextual','planner']:rows[name]=download('development-'+name+'.json')
cases=[];recordings={}
def compact(row):
    keys=['layout','seed','action','qualified','complete','checks','steps','physical_seconds','failure','fall','invalid_contact',
        'selection','plans','envelope','obstacles','travel_metrics','balance_metrics','loaded_foot_sliding_m','arm_travel_rad',
        'initial_physical_state_sha256','mechanics_sha256','receipt']
    return {k:row[k] for k in keys if k in row}
def append_cohort(cohort,split):
    for i,reference in enumerate(cohort['parent']):
        runs={}
        for name,attempts in cohort.items():
            r=next(x for x in attempts if (x['layout_sha256'],x['seed'])==(reference['layout_sha256'],reference['seed']))
            assert r['initial_physical_state_sha256']==reference['initial_physical_state_sha256']
            entry=r['public_recording'];filename=Path(entry['path']).name
            recordings[filename]={'path':entry['path'],'sha256':entry['sha256'],'bytes':entry['bytes']}
            runs[name]={'file':filename,'label':labels[name],'row':compact(r),'sha256':entry['sha256']}
        scope='Identical layout, sampled initial state, native gait, controller and verification. Model weights and selected commands may differ.'
        if args.compact and split=='development':scope='Audited deterministic action-table lookup. The model choice is new; the physical recording comes from the matching controller, layout and reset. This is not a new checkpoint rollout.'
        cases.append({'id':split+'-'+str(i),'kind':'navigation','label':('Fresh layout' if split=='final' else 'Development layout')+f' {i//2+1} · seed {reference["seed"]}',
            'split':split,'scope':scope,
            'layout_sha256':reference['layout_sha256'],'runs':runs})
append_cohort(rows,'final' if is_final else 'development')
if is_final:
    development={'parent':download(prefix+'development-u0.json')}
    for cp in report['checkpoints']:
        if cp['update']:
            key='selected' if cp['update']==selected else 'u'+str(cp['update'])
            development[key]=download(prefix+'development-u'+str(cp['update'])+'.json')
            labels[key]=f'Checkpoint · update {cp["update"]}'
    if args.compact:
        table=download('compact/data.json')['development_table'];fit=report['baselines']
        from mochi.navigation_v25.compact_baselines import contextual
        development['fixed']=[c['outcomes'][fit['fixed']] for c in table]
        development['contextual']=[c['outcomes'][contextual(c['observation'],fit['contextual'])] for c in table]
    else:
        for name in ['fixed','contextual','planner']:development[name]=download('development-'+name+'.json')
    append_cohort(development,'development')
from mochi.navigation_v23.baselines import summary
results=[]
for name,cohort in rows.items():
    s=summary(cohort)
    results.append({'cohort':'Fresh final layouts' if is_final else 'Development layouts','method':labels[name],
        'qualified':s['qualified'],'n':s['n'],'mean_steps':s['qualified_mean_steps']})
from mochi.navigation_v25.baselines import comparison
comp=comparison(rows['fixed'],rows.get('selected',rows['parent']))
claim=('The trained selector met the predeclared fixed-strategy comparison goal.' if comp['win'] else 'The trained selector has not demonstrated the predeclared improvement over the strongest fixed strategy.')
default=next((c['id'] for c in cases if c['runs'].get('selected') and c['runs']['selected']['row']['qualified'] and c['runs']['parent']['row']['qualified']
    and c['runs']['selected']['row']['steps']['attempts']<c['runs']['parent']['row']['steps']['attempts']),cases[0]['id'])
services=report.get('services',{});eligibility=services.get('eligibility',{})
usage=modal.Dict.from_name('mochi-continuation-v25-budget')[run]['usage']
navigation_updates=report.get('total_navigation_optimizer_updates',report['optimizer_updates_completed'])
manifest={'study':'mochi-continuation-v25','run_id':run,'status':report['status'],'default_case':default,'cases':cases,
    'summary':claim,'claim':claim+' '+('Final layouts were opened after checkpoint selection.' if is_final else 'These are development results. Final layouts remain unopened.'),
    'uncertainty':'Paired layout comparison against the training-selected fixed strategy: '+json.dumps(comp),
    'training':f'Tinker completed {navigation_updates} navigation optimizer updates to Qwen3.5-4B rank-16 LoRA weights. Training labels required both physics seeds to qualify. Replay balanced the measured winner classes. The parent and every checkpoint share the repaired actuator controller.'+(' The compact study uses two profiles and 32 training layouts; update 32 measures the representation change before 16 further weight updates. Development uses an exact-trajectory-audited outcome table. Every final comparison is a new physical rollout.' if args.compact else ''),
    'memory':f'{eligibility.get("writers",0)} writing identities, {eligibility.get("readers",0)} reading identities, {eligibility.get("cross_agent_reads",0)} source-verified cross-role recalls. Audience isolation: {eligibility.get("isolation_passed",False)}. This campaign used memory to pass findings between research stages; a causal memory-performance comparison is not claimed.',
    'execution':f'{usage["physical_rollouts"]} charged physical attempts; {usage["simulation_cpu_hours"]:.2f} simulation wall hours, including conservative reservations, at this publication snapshot. The amended cap is three Modal and two local physics workers. Provider costs are modeled, not invoices.',
    'totals':[[navigation_updates,'completed navigation optimizer updates'],[len({r['layout_sha256'] for r in rows['parent']}), 'final layouts' if is_final else 'development layouts'],[usage['physical_rollouts'],'charged physical attempts'],[eligibility.get('cross_agent_reads',0),'verified memory handoffs']],
    'results':results,'checkpoints':[dict(domain='navigation',**cp) for cp in report['checkpoints']],
    'sources':services.get('sources',[]),'recordings':recordings,'comparison':comp,
    'highlight_scope':'Default case is selected for inspectability after evaluation; it is not the aggregate result.'}
(web/'manifest.json').write_text(json.dumps(sanitize(manifest),indent=2)+'\n')
(evidence/'navigation-results.json').write_text(json.dumps(sanitize(report),indent=2)+'\n')
(evidence/'recordings.json').write_text(json.dumps(recordings,indent=2)+'\n')
print(json.dumps({'status':report['status'],'cases':len(cases),'recordings':len(recordings),'comparison':comp}),flush=True)
