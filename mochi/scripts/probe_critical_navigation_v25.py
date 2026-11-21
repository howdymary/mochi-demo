"""Test a saved checkpoint on a known development failure, never a final case."""
import asyncio
import json
from pathlib import Path
import modal

root=Path(__file__).resolve().parents[1]
async def main():
    run='mochi-nav25-20261121a';volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')
    fixed=json.loads(b''.join(volume.read_file(run+'/development-fixed.json')))
    # Fixed succeeds at seed 251000 here; earlier neural choices did not.
    reference=next(r for r in fixed if r['layout_sha256'].startswith('09de8063') and r['seed']==251000)
    assert reference['qualified']
    ident='critical-development-u32';target=root/'artifacts/continuation-v25'/f'{ident}.json';assert not target.exists()
    selection=await modal.Function.from_name('mochi-task-control-v25','choose').remote.aio('navigation',32,reference['observation'],ident)
    print(json.dumps({'checkpoint':32,'action':selection['action'],'stage':'Before the physical attempt; development only'}),flush=True)
    broker=modal.Function.from_name('mochi-continuation-v25','budget')
    await broker.remote.aio(run,ident+'-reserve',{'physical_rollouts':1,'simulation_cpu_hours':.1,'modeled_provider_usd':.02})
    row=await modal.Function.from_name('mochi-continuation-v25','trial').remote.aio(reference['layout'],reference['seed'],selection['action'],selection,ident)
    await broker.remote.aio(run,ident+'-actual',{'simulation_cpu_hours':row['receipt']['duration_seconds']/3600-.1})
    target.write_text(json.dumps({'reference':reference,'row':row,
        'scope':'Additional targeted development diagnosis. Not final evidence; no success threshold is changed.'},indent=2)+'\n')
    print(json.dumps({'checkpoint':32,'action':row['action'],'qualified':row['qualified'],'steps':row['steps']['attempts'],'checks':row['checks']}),flush=True)

if __name__=='__main__':asyncio.run(main())
