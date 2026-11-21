"""Supersede clearance-only optimism with measured full-sequence failures."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,existing_secrets,RUN

root=Path(__file__).resolve().parents[1]
app=modal.App('mochi-task-evidence-v25')


@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=.25,memory=1024,
    timeout=900,max_containers=1,retries=0,volumes={'/artifacts':volume})
async def correct(packet):
    from mochi.navigation_v23.services import NavigationServices
    await volume.reload.aio();d=Path('/artifacts')/RUN;target=d/'task-memory-correction.json'
    if target.exists():return json.loads(target.read_text())
    folder=d/'task-clearance-memory-correction';assert not (folder/'memory-journal.json').exists()
    old=json.loads((d/'task-clearance-memory/completed.json').read_text())
    ordinal=0;broker=modal.Function.from_name('mochi-continuation-v25','budget')
    async def charge(kind,amount):
        nonlocal ordinal
        ordinal+=1;await broker.remote.aio(RUN,'task-memory-correction-'+str(ordinal),{kind:amount})
    services=NavigationServices(RUN+'-r5',folder,charge,volume.commit.aio)
    services.records={r['id']:r for r in old['records']}
    for key in ['reads','calls','sources','decisions']:setattr(services,key,list(old[key]))
    finish='errored'
    try:
        await services.setup()
        private=await services.write('critic',{'kind':'synthetic-private-canary','value':'MOCHI_PRIVATE_CANARY_R5_CORRECTION'},private=True)
        await services.read('researcher',private,allowed=False)
        hypothesis=next(r['id'] for r in old['records'] if r['payload']['content']['kind']=='bounded-station-clearance-hypothesis')
        fact=await services.write('experimenter',{'kind':'full-controller-quality-correction','supersedes':hypothesis,
            'measured_evidence':packet,'finding':'Clearance-only component flags were insufficient. Full R5 sequences fail native acceleration; the selected local run also fails final sole support. R6/R7/R8 variants are rejected. No acceptance threshold changed.'})
        recalled=await services.read('critic',fact)
        decision=await services.decide('critic','Classify the R5 controller. Every quality constraint is mandatory. Object completion and clearance alone cannot establish qualified success.',
            recalled,['reject_r5_quality_failure','qualified_r5_success'],[fact])
        verdict=await services.write('critic',{'kind':'rejected-controller-verdict','source':fact,
            'model_classification':decision,'numerically_verified_classification':'reject_r5_quality_failure',
            'accepted':False,'qualification':'Preserve the negative result. Current final task study uses the original fully qualified R2 source and fixed navigation; it does not demonstrate combined learned navigation/manipulation.'})
        await services.read('researcher',verdict)
        plan=await services.write('researcher',{'kind':'qualified-next-study-scope','source':verdict,
            'decision':'Keep navigation final results and fixed-navigation task results separate. Do not promote R5 or its rejected refinements. Any later combined-controller study needs new unopened final scenarios.'})
        await services.read('designer',plan)
        result={'status':'completed','optimizer_updates_added':0,'physical_rollouts_added':0,
            'superseded_hypothesis':hypothesis,'services':services.report()}
        target.write_text(json.dumps(result,indent=2)+'\n');await volume.commit.aio();finish='success';return result
    finally:
        await services.http.aclose()
        if hasattr(services,'service'):await services.service.close(finish,detail='Owned task-evidence correction completed; training states retained')


@app.local_entrypoint()
def main():
    import gzip
    import hashlib
    d=root/'artifacts/continuation-v25';packet=[]
    for name in ['task-integration-r5-local-parent','task-integration-r5-local-selected','task-integration-r5-modal-parent']:
        raw=(d/(name+'.json.gz')).read_bytes();row=json.loads(gzip.decompress(raw));e=row['episode']
        packet.append({'id':name,'sha256':hashlib.sha256(raw).hexdigest(),
            'complete_sequence_success':row['complete_sequence_success'],'qualified_complete':row['qualified_complete'],
            'native_smoothness':e['native_smoothness'],'object_checks':{k:v['success'] for k,v in e['results'].items()},
            'fall':e['fall'],'invalid_contact':e['invalid_contact']})
    result=correct.remote(packet);out=root/'evidence/continuation-v25/task-memory-correction.json'
    assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'eligibility':result['services']['eligibility']}))
