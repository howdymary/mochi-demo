"""Identical frozen evaluation on the local CPU, cached for the Modal collector.

Training may use both CPU architectures. Every final checkpoint comparison
runs together on Modal. Local receipts retain their actual provider/architecture.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
import platform
from pathlib import Path
import time

import modal

root=Path(__file__).resolve().parents[1]
run=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id']


def one(request):
    index,seed,action=request
    from mochi.navigation_v25.engine import run as evaluate
    from mochi.integrations import digest
    from mochi.smooth_v16.public import rounded
    import torch
    torch.set_num_threads(1)
    volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
    broker=modal.Function.from_name('mochi-continuation-v25','budget')
    ident=f'r1-train-{index}-{seed}-{action}'
    folder=root/'artifacts/continuation-v25/local-training';folder.mkdir(exist_ok=True)
    summary=folder/(ident+'.summary.json')
    assert not summary.exists(),'No silent repeated local physical attempt'
    layout=json.loads((root/'configs/continuation-v25/training.json').read_text())[index]
    for name,expected in json.loads((root/'configs/continuation-v25/nav-source-freeze.json').read_text())['sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
    broker.remote(run,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1,'modeled_provider_usd':.02})
    start=time.perf_counter()
    row=evaluate(layout,seed,action,record=True)
    raw=gzip.compress(json.dumps(row,separators=(',',':')).encode(),compresslevel=1,mtime=0)
    target=folder/(ident+'.json.gz');target.write_bytes(raw)
    episode=row['episode']
    public={k:v for k,v in episode.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
    public['balance_measurements']=[{k:v for k,v in m.items() if k in ['t','phase','roll_rad','loads_n','step_category']} for m in episode['balance_measurements']]
    public['model_decisions']=episode['decisions']
    packed=gzip.compress(json.dumps(rounded(public),separators=(',',':')).encode(),mtime=0)
    clip=folder/(ident+'.public.json.gz');clip.write_bytes(packed)
    elapsed=time.perf_counter()-start
    row.update(request_sha256=digest([layout,seed,action,{}]),
        artifact={'path':run+'/physics/'+target.name,'sha256':hashlib.sha256(raw).hexdigest()},
        public_recording={'path':run+'/public/'+target.name,'sha256':hashlib.sha256(packed).hexdigest(),'bytes':len(packed)},
        receipt={'provider':'Local CPU','cpu':1,'memory_mib':None,'duration_seconds':elapsed,'architecture':platform.machine(),
            'scope':'Frozen evaluator on local CPU. Training data only; not a cloud execution or invoice. Same-seed candidate alternatives share this architecture.'},
        balance_metrics=episode['balance_metrics'],loaded_foot_sliding_m=sum(episode['foot_slip_estimate_m'].values()),contact_failures=episode['contact_failures'])
    row.pop('episode');row.pop('tracking')
    summary.write_text(json.dumps(row,indent=2)+'\n')
    # Upload the summary last. The cloud worker treats it as a completed cache.
    with volume.batch_upload() as batch:
        batch.put_file(target,'/'+row['artifact']['path'])
        batch.put_file(clip,'/'+row['public_recording']['path'])
    with volume.batch_upload() as batch:
        batch.put_file(summary,'/'+run+'/physics/'+summary.name)
    broker.remote(run,ident+'-actual',{'simulation_cpu_hours':elapsed/3600-.1})
    return {'id':ident,'qualified':row['qualified'],'failure':row['failure'],'steps':row['steps']['attempts'],'seconds':elapsed,'provider':'Local CPU'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=2);p.add_argument('--first',type=int,default=8);p.add_argument('--last',type=int,default=24);p.add_argument('--ascending',action='store_true');args=p.parse_args()
    assert 1<=args.workers<=3 and 4<=args.first<args.last<=32
    # Work backwards, well ahead of the ascending cloud collector, to avoid
    # competing for a request. Never use this to replace a running cloud input.
    order=range(args.first,args.last) if args.ascending else reversed(range(args.first,args.last))
    requests=[(i,s,a) for i in order for s in [251000,251001] for a in ['direct','buffered','wide_fast']]
    log=root/'artifacts/continuation-v25/local-collection.jsonl'
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(one,requests,chunksize=1):
            with log.open('a') as f:f.write(json.dumps(result)+'\n')
            print(json.dumps(result),flush=True)
