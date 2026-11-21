"""Source-verified review of the complete fresh navigation cohort. No training."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,existing_secrets,RUN

root=Path(__file__).resolve().parents[1]
app=modal.App('mochi-continuation-v25-review')


@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=.25,memory=1024,
    timeout=900,max_containers=1,retries=0,volumes={'/artifacts':volume})
async def review():
    from mochi.navigation_v23.services import NavigationServices
    from mochi.integrations import digest
    await volume.reload.aio();d=Path('/artifacts')/RUN
    target=d/'navigation-final-review.json';folder=d/'final-review-memory'
    if target.exists():return json.loads(target.read_text())
    assert not (folder/'memory-journal.json').exists(),'Inspect retained partial memory before retry'
    nav=json.loads((d/'compact/navigation-training.json').read_text());assert nav['status']=='completed'
    broker=modal.Function.from_name('mochi-continuation-v25','budget');ordinal=0
    async def charge(kind,amount):
        nonlocal ordinal
        ordinal+=1;await broker.remote.aio(RUN,'final-nav-review-'+str(ordinal),{kind:amount})
    services=NavigationServices(RUN+'-review',folder,charge,volume.commit.aio)
    finish='errored'
    try:
        await services.setup()
        packet={'kind':'fresh-navigation-observation','source_artifact':'compact/navigation-training.json',
            'source_sha256':digest(nav),'layouts':8,'seeds_per_layout':2,
            'selected_checkpoint':nav['selected_checkpoint'],
            'cohorts':nav['final'],'against_fixed':nav['final_against_fixed'],
            'against_parent':nav['final_against_parent'],'against_contextual':nav['final_against_contextual'],
            'qualification':'Every outcome is a fresh physical rollout after selection; no final result is a training label.'}
        observed=await services.write('experimenter',packet)
        evidence=await services.read('critic',observed)
        interpretation=await services.decide('critic',
            'Classify the additional training evidence. Passing the training-selected fixed control does not establish a gain over an earlier trained parent. Treat a contextual-control interval including one as uncertain. Do not infer native gait learning or a causal memory effect.',
            evidence,['gain_over_fixed_only','gain_over_fixed_and_parent','no_fixed_gain'],[observed])
        expected=('gain_over_fixed_and_parent' if nav['final_against_fixed']['win'] and nav['final_against_parent']['win']
            else 'gain_over_fixed_only' if nav['final_against_fixed']['win'] else 'no_fixed_gain')
        verdict=await services.write('critic',{'kind':'qualified-fresh-navigation-conclusion','evidence':observed,
            'model_interpretation':interpretation,'numerical_classification':expected,
            'conclusion':'The fixed-reference goal passed. The earlier parent remains more efficient. Further training has not established an incremental gain over that parent; the contextual comparison is uncertain.',
            'native_gait_weights_trained':False,'memory_benefit_established':False})
        await services.read('researcher',verdict)
        result={'status':'completed','source_sha256':digest(nav),'optimizer_updates_added':0,'physical_rollouts_added':0,
            'numerical_classification':expected,'model_interpretation':interpretation,'services':services.report()}
        target.write_text(json.dumps(result,indent=2)+'\n');await volume.commit.aio();finish='success';return result
    finally:
        await services.http.aclose()
        if hasattr(services,'service'):await services.service.close(finish,detail='Owned final evidence review ended; saved training states retained')


@app.local_entrypoint()
def main():
    result=review.remote();target=root/'evidence/continuation-v25/navigation-final-review.json'
    assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','numerical_classification','model_interpretation','optimizer_updates_added']}))
