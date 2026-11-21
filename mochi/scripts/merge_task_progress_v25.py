"""Retain the full task-checkpoint and engineering replays beside fresh navigation."""
import json
from pathlib import Path
import modal

root=Path(__file__).resolve().parents[1];d=root/'artifacts/continuation-v25'
target=root/'web/desk/continuation-v25/manifest.json';m=json.loads(target.read_text())
preview=json.loads((d/'preview-manifest-r4.json').read_text())
assert not any(c['kind']=='sequence' for c in m['cases'])
for case in preview['cases']:
    if case['kind']!='sequence':continue
    if case['id']=='task-weight-development':
        case['comparison_note']='Actual continuous R2 development runs with the same fixed navigation. Task update 8 qualified in 817 steps; updates 4 and 16 in 848. The parent missed sole clearance. The separate combined-model preflight uses a new shared task controller; its final results are pending.'
    m['cases'].append(case)
    for r in case['runs'].values():m['recordings'][r['file']]=preview['recordings'][r['file']]
m['results'] += [r for r in preview['results'] if r['cohort']=='Continuous task-model development']
v=modal.Volume.from_name('mochi-continuation-v25-artifacts');run=m['run_id']
tasks=json.loads(b''.join(v.read_file(run+'/task-training.json')))
m['checkpoints'] += [dict(c,domain='task and recovery') for c in tasks['checkpoints']]
m['totals'].append([16,'completed task and recovery optimizer updates'])
m['training']+=' The separate task/recovery adapter completed 16 optimizer updates; its development-selected update is eight. Four-task final results are pending.'
m['claim']+=' Four-task checkpoint replays below are development evidence; the new combined-model cohort is separate.'
seen={x['url'] for q in m['sources'] for x in q['sources']}
for q in preview['sources']+tasks['services']['sources']:
    sources=[s for s in q['sources'] if s['url'] not in seen]
    for s in sources:seen.add(s['url'])
    if sources:m['sources'].append(dict(q,sources=sources))
target.write_text(json.dumps(m,separators=(',',':'))+'\n')
print(json.dumps({'cases':len(m['cases']),'navigation_updates':48,'task_updates':16,'task_final_pending':True}))
