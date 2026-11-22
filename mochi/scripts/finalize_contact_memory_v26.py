"""Post-evaluation evidence handoff. Never feeds final outcomes into policies."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image, volume, existing_secrets, RUN

root = Path(__file__).resolve().parents[1]
app = modal.App('mochi-contact-evidence-v26')

@app.function(image=image, secrets=existing_secrets, serialized=True, cpu=.25, memory=1024,
    timeout=900, max_containers=1, retries=0, volumes={'/artifacts': volume})
async def review(packet):
    from mochi.navigation_v23.services import NavigationServices
    await volume.reload.aio()
    directory = Path('/artifacts') / RUN
    output = directory / 'contact26-final-memory.json'
    if output.exists():
        return json.loads(output.read_text())
    ordinal = 0
    broker = modal.Function.from_name('mochi-continuation-v25', 'budget')
    async def charge(kind, amount):
        nonlocal ordinal
        ordinal += 1
        await broker.remote.aio(RUN, f'contact26-final-memory-{ordinal}', {kind: amount})
    services = NavigationServices(RUN + '-c26', directory / 'contact26-final-memory', charge, volume.commit.aio)
    finish = 'errored'
    try:
        await services.setup()
        canary = await services.write('critic', {'kind': 'synthetic-private-canary', 'value': 'MOCHI_PRIVATE_CANARY_C26'}, private=True)
        await services.read('researcher', canary, allowed=False)
        fact = await services.write('experimenter', {'kind': 'contact-continuation-measurements', 'evidence': packet,
            'qualification': 'All original task-final failures retained. Controller revisions are engineering. Tinker updates remain 64 and native gait weights remain fixed.'})
        observation = await services.read('researcher', fact)
        hypothesis = await services.write('researcher', {'kind': 'contact-versus-selection-distinction', 'source': fact,
            'finding': 'The original final cohort localized failure at laptop contact. A shared controller repair must pass full physical checks before model weights can be meaningfully compared. Component success is insufficient.',
            'measured_packet_sha256': observation['evidence']['packet_sha256']})
        recalled = await services.read('designer', hypothesis)
        plan = await services.write('designer', {'kind': 'contact-study-control-plan', 'source': hypothesis,
            'used_recalled_finding': recalled['finding'],
            'decision': 'Keep engineering and checkpoint comparisons separate. Preserve failures, compare identical source and resets, and do not train on opened final outcomes.'})
        await services.read('experimenter', plan)
        measured = await services.read('critic', fact)
        classification = await services.decide('critic', 'Review the completed paired R2 contact cohort. State whether all six selected-model attempts completed within every original quality check. Later engineering studies are separate. Do not attribute shared controller engineering to model training.',
            measured, ['paired_r2_selected_all_qualified', 'paired_r2_target_unmet'], [fact, plan])
        numerical = 'paired_r2_selected_all_qualified' if packet.get('selected_final_qualified') == 6 else 'paired_r2_target_unmet'
        verdict = await services.write('critic', {'kind': 'contact-continuation-verdict', 'sources': [fact, plan],
            'model_classification': classification, 'numerical_classification': numerical,
            'qualification': 'Numerical physical gates determine promotion. Preserve any model/numerical disagreement. This handoff occurs after evaluation and provides no causal memory-benefit estimate.'})
        await services.read('researcher', verdict)
        result = {'status': 'completed', 'optimizer_updates_added': 0, 'physical_rollouts_added': 0,
            'numerical_classification': numerical, 'services': services.report()}
        output.write_text(json.dumps(result, indent=2) + '\n')
        await volume.commit.aio()
        finish = 'success'
        return result
    finally:
        await services.http.aclose()
        if hasattr(services, 'service'):
            await services.service.close(finish, detail='Owned post-evaluation evidence handoff ended; checkpoints retained')

@app.local_entrypoint()
def main():
    import hashlib
    directory = root / 'evidence/continuation-v25'
    original = json.loads((directory / 'task-final-assessment.json').read_text())
    contact = directory / 'contact26-final-assessment.json'
    updated = json.loads(contact.read_text()) if contact.exists() else None
    packet = {'original_final': {side: {k: v for k, v in rows.items() if k != 'attempts'} for side, rows in original['models'].items()},
        'new_final': {side: {k: v for k, v in rows.items() if k != 'attempts'} for side, rows in updated['models'].items()} if updated else None,
        'original_assessment_sha256': hashlib.sha256((directory / 'task-final-assessment.json').read_bytes()).hexdigest(),
        'new_assessment_sha256': hashlib.sha256(contact.read_bytes()).hexdigest() if contact.exists() else None,
        'selected_final_qualified': updated['models']['selected']['qualified'] if updated else None,
        'not_training_labels': True}
    packet['packet_sha256'] = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
    result = review.remote(packet)
    target = directory / 'contact26-final-memory.json'
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'numerical_classification': result['numerical_classification'], 'eligibility': result['services']['eligibility']}))
