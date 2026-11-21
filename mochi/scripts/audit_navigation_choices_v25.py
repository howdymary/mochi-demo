"""Training-only diagnostic of conditional versus constant profile choices."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import modal

root=Path(__file__).resolve().parents[1];run='mochi-nav25-20261121a'
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
data=json.loads(b''.join(volume.read_file(run+'/collection-training24.json')))
target=root/'artifacts/continuation-v25/training-action-audit-u32.json';assert not target.exists()
choose=modal.Function.from_name('mochi-task-control-v25','choose')
def one(pair):
    i,row=pair
    value=choose.remote('navigation',32,row['observations'][0],f'training-action-audit-u32-{i}')
    return {'layout_sha256':row['layout_sha256'],'target':row['target'],**value}
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(one,enumerate(data['records'])))
report={'checkpoint':32,'rows':rows,'counts':dict(Counter(r['action'] for r in rows)),
    'target_agreements':sum(r['action']==r['target'] for r in rows),
    'scope':'Training-only conditional-choice diagnostic. No new physical rollouts or final layout information. Does not select checkpoints.'}
target.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['checkpoint','counts','target_agreements','scope']}))
