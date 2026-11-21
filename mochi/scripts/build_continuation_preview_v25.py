"""A labeled progress replay, separating training probes and engineering."""
import gzip
import hashlib
import json
from pathlib import Path
import modal
from mochi.smooth_v16.public import rounded

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
web=root/'web/desk/continuation-v25';web.mkdir(exist_ok=True)
run='mochi-nav25-20261121a';volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
report=json.loads(b''.join(volume.read_file(run+'/navigation-training.json')))
probe=json.loads((directory/'first-trained-physical-probe.json').read_text());assert len(probe['rows'])==2
cases=[];recordings={};results=[]
runs={}
for i,row in enumerate(probe['rows']):
    entry=row['public_recording'];file=Path(entry['path']).name
    recordings[file]=entry
    label='Parent · update 0' if i==0 else 'Checkpoint · update 8'
    runs['parent' if i==0 else 'selected']={'file':file,'row':row,'label':label,'sha256':entry['sha256']}
    results.append({'cohort':'Known training-layout probe','method':label,'qualified':int(row['qualified']),'n':1,'mean_steps':row['steps']['attempts'] if row['qualified'] else None})
cases.append({'id':'training-probe','label':'Saved-weight physical probe · training layout','kind':'navigation','split':'training',
    'layout_sha256':probe['rows'][0]['layout_sha256'],'runs':runs,'scope':probe['scope'],
    'comparison_note':'Both checkpoints were sampled through Tinker before new physical rollouts. The parent arrived but missed the foot-clearance check. Update 8 selected wide_fast and qualified. This known training layout is not fresh-test evidence.'})
runs={}
for i,ident in enumerate(['sequence-native-r3','sequence-clearance-r4']):
    raw=(directory/(ident+'.json.gz')).read_bytes();row=json.loads(gzip.decompress(raw));episode=row['episode']
    clip={k:v for k,v in episode.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
    clip['balance_measurements']=[{k:v for k,v in r.items() if k in ['t','phase','roll_rad','loads_n','step_category']} for r in episode['balance_measurements']]
    clip['model_decisions']=episode['decisions']
    packed=gzip.compress(json.dumps(rounded(clip),separators=(',',':')).encode(),mtime=0)
    file='engineering-'+ident+'.json.gz';local=directory/file;local.write_bytes(packed)
    with volume.batch_upload() as batch:batch.put_file(local,'/'+run+'/public/'+file)
    digest=hashlib.sha256(packed).hexdigest();recordings[file]={'path':run+'/public/'+file,'sha256':digest,'bytes':len(packed)}
    metadata=json.loads((directory/(ident+'.metadata.json')).read_text())
    label='Before globe repair · engineering' if i==0 else 'After globe repair · engineering'
    runs['parent' if i==0 else 'selected']={'file':file,'label':label,'sha256':digest,'fingerprint':metadata['source_sha256'],'updates':0,
        'row':{'kind':'sequence','qualified_complete':row['qualified_complete'],'steps':episode['steps']['attempts'],
            'duration':episode['duration'],'failure':row['failure'],'action':'fixed task profiles; shared controller engineering'}}
    results.append({'cohort':'Continuous controller-development run','method':label,'qualified':int(row['qualified_complete']),'n':1,'mean_steps':episode['steps']['attempts'] if row['qualified_complete'] else None})
cases.append({'id':'globe-engineering','label':'Four-task sequence · globe controller repair','kind':'sequence','split':'engineering',
    'layout_sha256':metadata['layout_sha256'],'runs':runs,
    'scope':'Two complete, uninterrupted runs in the same scene. This comparison changes controller code and credits zero Tinker updates.',
    'comparison_note':'The earlier run completed the tasks but missed the globe-leg foot-clearance limit. The repaired run passed all checks in 752 steps. A subsequent physics seed exposed a descent fall; robustness work continues.'})
usage=modal.Dict.from_name('mochi-continuation-v25-budget')[run]['usage']
manifest={'study':'mochi-continuation-v25','run_id':run,'status':'running','default_case':'training-probe','cases':cases,'recordings':recordings,
    'summary':'Saved Tinker weights now change a physical navigation outcome. A separate controller repair completes the four-task sequence. Fresh-layout evaluation is running.',
    'claim':'Progress preview. The trained model has not yet demonstrated the fixed-strategy goal on fresh layouts. One fully qualified controller-development run does not establish robust four-task completion.',
    'uncertainty':'One known training-layout checkpoint probe and one controller-development comparison. Neither is an estimate of generalization. The eight-layout final navigation cohort remains unopened.',
    'training':f'Tinker has completed {report["optimizer_updates_completed"]} rank-16 LoRA optimizer updates on Qwen3.5-4B. Targets came from 144 physical requests across 24 training layouts and two physics seeds. Replay balances direct, buffered and wide_fast winners. The pretrained native gait network is fixed.',
    'memory':'Source-verified past.dev recalls pass measured failures, research and replay allocation between application roles. A private-audience canary passed. Evaluation conclusions are pending.',
    'execution':f'Training data includes 24 Modal and 120 local CPU requests. These two checkpoint probes are new Modal physical runs. The shared ledger accounts for {usage["physical_rollouts"]} physical attempts, including failed engineering and the separately preserved duplicate. Usage estimates are not invoices.',
    'totals':[[report['optimizer_updates_completed'],'completed navigation optimizer updates'],[24,'training layouts'],[144,'measured training requests'],[1,'qualified controller-development sequence']],
    'results':results,'checkpoints':[dict(domain='navigation',**c) for c in report['checkpoints']],
    'sources':report['services']['sources'],'highlight_scope':'The training probe was selected in advance because the frozen parent missed a physical-quality check there. It does not enter checkpoint selection.'}
(web/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(directory/'preview-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'cases':len(cases),'recordings':len(recordings),'updates':report['optimizer_updates_completed'],'final_opened':report['final_opened']}),flush=True)
