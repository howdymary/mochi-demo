"""Failure-driven Exa research and source-verified cross-role planning memory."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,existing_secrets,RUN

root=Path(__file__).resolve().parents[1]
app=modal.App('mochi-heading-research-v26')

@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=.25,memory=1024,
    timeout=900,max_containers=1,retries=0,volumes={'/artifacts':volume})
async def investigate(packet):
    from mochi.navigation_v23.services import NavigationServices
    await volume.reload.aio();directory=Path('/artifacts')/RUN;out=directory/'heading-research.json'
    if out.exists():return json.loads(out.read_text())
    ordinal=0;broker=modal.Function.from_name('mochi-continuation-v25','budget')
    async def charge(kind,value):
        nonlocal ordinal
        ordinal+=1;await broker.remote.aio(RUN,f'heading-research-v26-{ordinal}',{kind:value})
    services=NavigationServices(RUN+'-h26',directory/'heading-research',charge,volume.commit.aio)
    finish='errored'
    try:
        await services.setup()
        private=await services.write('critic',{'kind':'synthetic-private-canary','value':'MOCHI_PRIVATE_CANARY_H26'},private=True)
        await services.read('researcher',private,allowed=False)
        fact=await services.write('experimenter',{'kind':'reached-waypoint-tracking-error','evidence':packet,
            'observation':'A nominally feasible oriented route reached its first waypoint with 11.024 mm position error inside the existing 12 mm arrival tolerance. The subsequent reached-state collision check rejected the next segment. No collision or fall occurred. Static feasibility alone did not establish executable navigation.'})
        recalled=await services.read('researcher',fact)
        search=await services.search('robot motion planning tracking error footprint inflation robust swept volume humanoid footstep turning clearance')
        evidence=await services.write('researcher',{'kind':'tracking-margin-research','source':fact,'sources':search['sources'],
            'testable_hypothesis':'Planning must reserve room for measured tracking error as well as the nominal body and feet. Compare a bounded sampled tracking envelope with the rejected nominal route. Keep physical collision and quality verifiers unchanged.',
            'observation_used':recalled['observation']})
        research=await services.read('designer',evidence)
        choice=await services.decide('designer','Select the next bounded engineering experiment from the failure and sourced research. Do not weaken any verifier or claim native gait learning.',
            research,['reserve_measured_tracking_clearance','increase_actuator_feedback_gains','insufficient_evidence'],[fact,evidence])
        plan=await services.write('designer',{'kind':'tracking-clearance-experiment-plan','source':evidence,
            'model_choice':choice,'proposed_test':'A sampled 16 mm translation envelope around nominal route segments covers the 12 mm arrival tolerance plus 4 mm reserve. Existing heading and foot-clearance checks still apply. Test physically from reset before opening the new validation set.',
            'qualification':'This is shared controller/planner engineering, with the already frozen navigation-48/task-8 weights. No additional optimizer update.'})
        await services.read('experimenter',plan);await services.read('critic',plan)
        verdict=await services.write('critic',{'kind':'unverified-geometric-hypothesis','sources':[fact,evidence,plan],
            'accepted_as_performance_improvement':False,'condition':'Require a qualified uninterrupted development run and prospective validation. A sampled envelope is a bounded diagnostic, not a formal proof of all tracking disturbances.'})
        await services.read('researcher',verdict)
        result={'status':'completed','optimizer_updates_added':0,'physical_rollouts_added':0,'services':services.report()}
        out.write_text(json.dumps(result,indent=2)+'\n');await volume.commit.aio();finish='success';return result
    finally:
        await services.http.aclose()
        if hasattr(services,'service'):await services.service.close(finish,detail='Owned tracking-clearance research ended; checkpoints retained')

@app.local_entrypoint()
def main():
    d=root/'artifacts/continuation-v25';meta=json.loads((d/'contact26r3-dev-selected.metadata.json').read_text())
    result=investigate.remote({'id':meta['id'],'physical_record_sha256':meta['sha256'],
        'failure':meta['failure'],'reached_position_error_mm':11.024263976546962,
        'position_tolerance_mm':12.,'source_freeze_sha256':meta['source_freeze_sha256'],'native_gait_weights_fixed':True})
    out=root/'evidence/continuation-v25/heading-research.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'eligibility':result['services']['eligibility']}))
