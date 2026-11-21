"""Read-only weight comparison after the bounded optimizer campaign finishes.

Creates named, expiring external exports of this study's own saved states.
Never deletes or changes the original parent or optimizer checkpoints.
"""
import json
import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
RUN = json.loads((ROOT / 'configs/continuation-v25/protocol.json').read_text())['id']
app = modal.App('mochi-continuation-v25-weight-audit')
volume = modal.Volume.from_name('mochi-continuation-v25-artifacts')
image = (modal.Image.debian_slim(python_version='3.11')
    .pip_install('torch==2.15.0', index_url='https://download.pytorch.org/whl/cpu')
    .pip_install('tinker==0.39.2', 'httpx==0.28.1', 'safetensors==0.7.0', 'numpy==2.3.4'))
secrets = [modal.Secret.from_name(n) for n in ['compute-forecast-signals-v6', 'compute-forecast-evidence-future-v15']]


@app.function(image=image, secrets=secrets, serialized=True, cpu=1, memory=4096,
              timeout=1200, max_containers=1, retries=0, volumes={'/artifacts': volume})
async def audit(run,kind,update):
    owned=[];finish='errored'
    async def perform():
        import hashlib
        import httpx
        import numpy as np
        import tinker
        from safetensors.torch import load_file
        directory = Path('/artifacts') / run
        await volume.reload.aio()
        assert kind in ['navigation','task','compact_navigation']
        report_path='compact/navigation-training.json' if kind=='compact_navigation' else kind+'-training.json'
        report = json.loads((directory / report_path).read_text())
        assert report.get('total_navigation_optimizer_updates',report['optimizer_updates_completed']) >= update > 0
        target = directory / (kind+'-weight-tensor-audit-u'+str(update)+'-r2.json')
        assert not target.exists(), 'Preserve the first weight audit'
        paths_name='compact/private-navigation-paths.json' if kind=='compact_navigation' else 'private-'+kind+'-paths.json'
        paths = json.loads((directory / paths_name).read_text())
        rest, service = tinker.RestClient(), tinker.ServiceClient(display_name=run + '-weight-audit')
        owned.append(service)
        exports, arrays = [], []
        async with httpx.AsyncClient(timeout=180) as http:
            target_update = update
            for checkpoint_update in [32 if kind=='compact_navigation' else 0, target_update]:
                trainer = await service.create_training_client_from_state(paths[str(checkpoint_update)]['optimizer'])
                saved = await trainer.save_weights_external('mochi25-'+kind+'-tensor-audit-u'+str(checkpoint_update), ttl_seconds=86400)
                links = await rest.get_external_weights_urls(saved.path)
                dest = directory / 'private-weight-exports' / kind / str(checkpoint_update)
                dest.mkdir(parents=True, exist_ok=False)
                tensors, files = {}, []
                for name, url in links.urls.items():
                    relative = Path(name)
                    assert not relative.is_absolute() and '..' not in relative.parts
                    content = (await http.get(url)).raise_for_status().content
                    file = dest / relative
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(content)
                    files.append({'name': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
                    if file.suffix == '.safetensors':
                        tensors.update({k: v.detach().float().numpy() for k, v in load_file(str(file)).items()})
                assert tensors, 'No inspectable LoRA tensors were exported'
                arrays.append(tensors)
                exports.append({'update': checkpoint_update, 'checkpoint_id': hashlib.sha256(json.dumps(paths[str(checkpoint_update)]['optimizer'], sort_keys=True).encode()).hexdigest(),
                    'export_files': files, 'tensor_count': len(tensors),
                    'tensor_elements': sum(v.size for v in tensors.values())})
        assert arrays[0].keys() == arrays[1].keys()
        changed, maximum, squared = [], 0., 0.
        for name in arrays[0]:
            a, b = arrays[0][name].astype(np.float64), arrays[1][name].astype(np.float64)
            assert a.shape == b.shape
            difference = b - a
            if np.any(difference):
                changed.append(name)
            maximum = max(maximum, float(abs(difference).max()))
            squared += float(np.sum(difference ** 2))
        assert changed and maximum > 0
        result = {'status': 'completed', 'run_id': run, 'optimizer_updates_in_audit': 0, 'exports': exports,
            'changed_tensor_count': len(changed), 'changed_tensor_names': changed,
            'maximum_absolute_parameter_difference': maximum, 'l2_parameter_difference': squared ** .5,
            'native_gait_updated': False, 'original_states_deleted': False,
            'qualification': 'Numerical comparison of exported adapter tensors. This proves weight changes, not better navigation. Original training states remain intact. New external copies expire after one day. Download URLs and private state paths are withheld.'}
        target.write_text(json.dumps(result, indent=2) + '\n')
        await volume.commit.aio()
        return result
    try:
        result=await perform();finish='success';return result
    except BaseException as error:
        # Never expose a signed download URL or private state path in errors.
        result = {"status": "incomplete", "run_id": run, "error_type": type(error).__name__,
            "optimizer_updates_in_audit": 0, "qualification": "External tensor comparison unavailable; original checkpoints remain intact."}
        target = Path('/artifacts') / run / (kind+'-weight-tensor-audit-u'+str(update)+'-r2.json')
        if not target.exists():
            target.write_text(json.dumps(result, indent=2) + "\n")
            await volume.commit.aio()
        return result
    finally:
        for service in owned:
            await service.close(finish,detail='Owned read-only tensor audit ended; original optimizer states retained')


@app.local_entrypoint()
def main(kind: str, update: int):
    result = audit.remote(RUN,kind,update)
    out = ROOT / ('evidence/continuation-v25/'+kind+'-weight-tensor-audit-u'+str(update)+'-r2.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'error_type', 'changed_tensor_count', 'maximum_absolute_parameter_difference', 'native_gait_updated'] if k in result}))
