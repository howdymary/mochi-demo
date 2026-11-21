"""Check read-only forward scoring against an earlier completed sampler result."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,existing_secrets,RUN

app=modal.App('mochi-continuation-v25-forward-diagnostic')
@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=1,memory=4096,timeout=300,retries=0,volumes={'/artifacts':volume})
async def probe():
    import asyncio,time
    import torch
    import tinker
    from tinker_cookbook import renderers,model_info
    from tinker_cookbook.recipes.decisions import DecisionRenderer,decision_choice_datums
    from mochi.navigation_v25.engine import decision,ACTIONS
    from mochi.integrations import digest
    await volume.reload.aio();directory=Path('/artifacts')/RUN
    service=tinker.ServiceClient(display_name=RUN+'-readonly-forward-probe');status='interrupted'
    try:
        path=json.loads((directory/'private-navigation-paths.json').read_text())['0']['optimizer']
        old=json.loads((directory/'physics/first-training-probe-u0.summary.json').read_text())
        assert old['selection']['checkpoint_id']==digest(path)
        trainer=await service.create_training_client_from_state(path)
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),trainer.get_tokenizer()))
        datums=decision_choice_datums(renderer,[(decision(old['observation']),a) for a in ACTIONS])
        tokens=sum(d.model_input.length for d in datums)
        await modal.Function.from_name('mochi-continuation-v25','budget').remote.aio(RUN,'readonly-forward-probe',{'inference_input_plus_max_output_tokens':tokens,'modeled_provider_usd':tokens*1.01/1e6})
        started=time.perf_counter()
        try:
            result=await asyncio.wait_for(trainer.forward(datums,loss_fn='cross_entropy'),timeout=120)
            scores=[]
            for datum,output in zip(datums,result.loss_fn_outputs,strict=True):
                index=torch.nonzero(datum.loss_fn_inputs['weights'].to_torch()).reshape(-1)
                assert len(index)==1
                scores.append(float(output['logprobs'].to_torch()[int(index[0])]))
            distribution=dict(zip(ACTIONS,torch.softmax(torch.tensor(scores,dtype=torch.float64),0).tolist(),strict=True))
            delta=max(abs(distribution[a]-old['selection']['distribution'][a]) for a in ACTIONS)
            response={'status':'completed','distribution':distribution,'saved_sampling_distribution':old['selection']['distribution'],
                'maximum_probability_difference':delta,'matches_within_0_001':delta<=.001,
                'inference_seconds':time.perf_counter()-started,'optimizer_updates':0,'backward_calls':0,
                'scope':'Read-only model forward pass, checked against a previously completed sampling request. No new physical rollout or model update.'};status='success'
        except TimeoutError:response={'status':'timeout','wait_seconds':time.perf_counter()-started,'optimizer_updates':0,'backward_calls':0}
        (directory/'compact/forward-inference-probe.json').write_text(json.dumps(response,indent=2)+'\n');await volume.commit.aio();return response
    finally:await service.close(status,detail='Owned read-only forward diagnostic complete')

@app.local_entrypoint()
def main():
    result=probe.remote();root=Path(__file__).resolve().parents[1]
    (root/'artifacts/continuation-v25/forward-inference-probe.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
