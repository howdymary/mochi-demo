"""Charged controller diagnosis on training layouts, outside checkpoint evaluation."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import modal

p=argparse.ArgumentParser()
p.add_argument('--id',required=True)
p.add_argument('--mode',choices=['native-arms','old-navigation','old-reset'],required=True)
p.add_argument('--action',default='wide_fast')
p.add_argument('--index',type=int,default=0)
args=p.parse_args()
root=Path(__file__).resolve().parents[1]
out=root/'artifacts/continuation-v25'/(args.id+'.json.gz')
assert not out.exists()
from mochi.navigation_v25 import engine,navigation
from mochi.balanced.onnx_walk import HubWalker
if args.mode=='native-arms':
    navigation.HubWalker=HubWalker
elif args.mode=='old-navigation':
    from mochi.navigation_v23.navigation import navigate
    engine.navigate=navigate
elif args.mode=='old-reset':
    from mochi.navigation_v23.world import NavigationWorld
    engine.NavigationWorld=NavigationWorld
layout=json.loads((root/'configs/continuation-v25/training.json').read_text())[args.index]
broker=modal.Function.from_name('mochi-continuation-v25','budget')
run=json.loads((root/'configs/continuation-v25/protocol.json').read_text())['id']
broker.remote(run,args.id+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1})
t=time.perf_counter()
r=engine.run(layout,251000,args.action,record=True)
r['diagnostic']={'mode':args.mode,'scope':'Shared-controller engineering probe on training geometry; no learned weights.'}
out.write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0))
elapsed=time.perf_counter()-t
broker.remote(run,args.id+'-actual',{'simulation_cpu_hours':elapsed/3600-.1})
print(json.dumps({k:r[k] for k in ['diagnostic','failure','fall','invalid_contact','qualified','checks','steps','physical_seconds','arrivals']})[:6000],flush=True)
