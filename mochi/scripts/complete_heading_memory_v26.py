"""Close the sourced tracking-clearance hypothesis with actual physical outcomes."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,existing_secrets,RUN

root=Path(__file__).resolve().parents[1];app=modal.App('mochi-heading-outcomes-v26')

@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=.25,memory=1024,timeout=900,max_containers=1,retries=0,volumes={'/artifacts':volume})
async def complete(packet):
    from mochi.navigation_v23.services import NavigationServices
    await volume.reload.aio();directory=Path('/artifacts')/RUN;target=directory/'heading-outcome-memory.json'
    if target.exists():return json.loads(target.read_text())
    prior=json.loads((directory/'heading-research.json').read_text())['services']
    ordinal=0;broker=modal.Function.from_name('mochi-continuation-v25','budget')
    async def charge(kind,value):
        nonlocal ordinal
        ordinal+=1;await broker.remote.aio(RUN,f'heading-outcome-v26-{ordinal}',{kind:value})
    services=NavigationServices(RUN+'-h26',directory/'heading-outcome-memory',charge,volume.commit.aio)
    services.records={r['id']:r for r in prior['records']}
    for key in ['reads','calls','sources','decisions']:setattr(services,key,list(prior[key]))
    finish='errored'
    try:
        await services.setup()
        plan=next(r['id'] for r in prior['records'] if r['payload']['content']['kind']=='tracking-clearance-experiment-plan')
        await services.read('experimenter',plan)
        fact=await services.write('experimenter',{'kind':'tracking-envelope-physical-results','plan':plan,'evidence':packet,
            'qualification':'Physical measurements close the hypothesis. Shared engineering, fixed model weights, unchanged success checks. No causal memory or training gain is claimed.'})
        recalled=await services.read('critic',fact)
        choice=await services.decide('critic','Assess the R4 tracking-clearance engineering experiment. Acceptance requires a qualified development run and all three prospective product attempts within every original quality check. An unopened set is untested, not a failed trial. This is not a model-weight comparison.',
            recalled,['all_declared_physical_tests_qualified','target_not_demonstrated'],[plan,fact])
        numerical='all_declared_physical_tests_qualified' if packet['development']['qualified_complete'] and packet.get('product_qualified')==3 else 'target_not_demonstrated'
        verdict=await services.write('critic',{'kind':'tracking-envelope-qualified-verdict','sources':[plan,fact],
            'model_choice':choice,'numerical_classification':numerical,
            'qualification':'A small selected-model engineering validation. Broader paired-model task reliability and native gait learning remain unestablished. The numerical gates determine promotion.'})
        await services.read('researcher',verdict)
        result={'status':'completed','optimizer_updates_added':0,'physical_rollouts_added':0,'numerical_classification':numerical,
            'new_reads':len(services.reads)-len(prior['reads']),'new_records':len(services.records)-len(prior['records']),'services':services.report()}
        target.write_text(json.dumps(result,indent=2)+'\n');await volume.commit.aio();finish='success';return result
    finally:
        await services.http.aclose()
        if hasattr(services,'service'):await services.service.close(finish,detail='Owned physical-outcome handoff ended; checkpoints retained')

@app.local_entrypoint()
def main():
    directory=root/'artifacts/continuation-v25'
    dev=json.loads((directory/'contact26r4-dev-selected.metadata.json').read_text())
    product=directory/'heading26-product-final.json';report=json.loads(product.read_text()) if product.exists() else None
    keys=['id','qualified_complete','failure','steps','physical_seconds','sha256','source_freeze_sha256']
    packet={'development':{k:dev[k] for k in keys},'product_qualified':report['qualified'] if report else None,
        'product_attempts':[{k:r[k] for k in keys} for r in report['results']] if report else None,
        'product_opened':(directory/'heading26-final-opened.json').exists(),'optimizer_updates_added':0}
    result=complete.remote(packet);out=root/'evidence/continuation-v25/heading-outcome-memory.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'numerical_classification':result['numerical_classification'],'new_records':result['new_records'],'new_reads':result['new_reads']}))
