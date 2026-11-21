"""A declared training-layout physical probe of actual saved model weights."""
import asyncio
import json
from pathlib import Path
import modal

root=Path(__file__).resolve().parents[1]


async def main():
    run='mochi-nav25-20261121a'
    target=root/'artifacts/continuation-v25/first-trained-physical-probe.json';assert not target.exists()
    layout=json.loads((root/'configs/continuation-v25/training.json').read_text())[1]
    seed=251001
    observed=await modal.Function.from_name('mochi-task-control-v25','observe').remote.aio(layout,seed)
    choose=modal.Function.from_name('mochi-task-control-v25','choose')
    broker=modal.Function.from_name('mochi-continuation-v25','budget')
    trial=modal.Function.from_name('mochi-continuation-v25','trial')
    rows=[]
    for update in [0,8]:
        ident=f'first-training-probe-u{update}'
        selection=await choose.remote.aio('navigation',update,observed,ident)
        await broker.remote.aio(run,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1,'modeled_provider_usd':.02})
        row=await trial.remote.aio(layout,seed,selection['action'],selection,ident)
        await broker.remote.aio(run,ident+'-actual',{'simulation_cpu_hours':row['receipt']['duration_seconds']/3600-.1})
        rows.append(row)
        target.write_text(json.dumps({'scope':'Physically executed saved-checkpoint probe on a known training layout. Not held-out evidence and not used for checkpoint selection.','rows':rows},indent=2)+'\n')
        print(json.dumps({'update':update,'action':row['action'],'qualified':row['qualified'],'steps':row['steps']['attempts']}),flush=True)


if __name__=='__main__':asyncio.run(main())
