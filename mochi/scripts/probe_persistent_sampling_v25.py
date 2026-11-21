"""Compare named sampler weights with the stalled ephemeral snapshot path."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,existing_secrets,RUN

app=modal.App('mochi-continuation-v25-sampling-diagnostic')
@app.function(image=image,secrets=existing_secrets,serialized=True,cpu=1,memory=2048,timeout=360,retries=0,volumes={'/artifacts':volume})
async def probe():
    import asyncio,time
    import tinker
    from tinker_cookbook import renderers,model_info
    from tinker_cookbook.recipes.decisions import DecisionRenderer,sample_decision
    from mochi.navigation_v25.compact import decision
    from mochi.integrations import digest
    await volume.reload.aio();directory=Path('/artifacts')/RUN/'compact'
    service=tinker.ServiceClient(display_name=RUN+'-persistent-probe')
    status='interrupted'
    try:
        path=json.loads((directory/'private-navigation-paths.json').read_text())['0']['optimizer']
        trainer=await service.create_training_client_from_state(path)
        saved=await trainer.save_weights_for_sampler(name='mochi25-persistent-probe-zero',ttl_seconds=3600)
        private=directory/'private-persistent-probe.json';assert not private.exists()
        private.write_text(json.dumps({'sampler_path':saved.path})+'\n');await volume.commit.aio()
        sampler=await service.create_sampling_client(model_path=saved.path)
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),trainer.get_tokenizer()))
        obs=json.loads((directory/'data.json').read_text())['development_table'][0]['observation']
        rendered=renderer.render(decision(obs));tokens=len(rendered.tokens)+1
        await modal.Function.from_name('mochi-continuation-v25','budget').remote.aio(RUN,'persistent-probe-inference',{'inference_input_plus_max_output_tokens':tokens,'modeled_provider_usd':tokens*1.01/1e6})
        start=time.perf_counter()
        try:
            distribution=await asyncio.wait_for(sample_decision(sampler,rendered),timeout=120)
            result={'status':'completed','distribution':distribution,'inference_seconds':time.perf_counter()-start,'weights_sha256':digest(saved.path),'optimizer_updates':0};status='success'
        except TimeoutError:result={'status':'timeout','wait_seconds':time.perf_counter()-start,'optimizer_updates':0}
        (directory/'persistent-sampling-probe.json').write_text(json.dumps(result,indent=2)+'\n');await volume.commit.aio();return result
    finally:
        await service.close(status,detail='Owned sampling diagnostic complete; saved states retained')

@app.local_entrypoint()
def main():
    result=probe.remote();root=Path(__file__).resolve().parents[1]
    (root/'artifacts/continuation-v25/persistent-sampling-probe.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
