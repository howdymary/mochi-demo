"""V25 shared budget and bounded physics workers; older apps are untouched."""
import json
import os
from pathlib import Path
import modal
from mochi.navigation_v23.remote import base_image, existing_secrets

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = json.loads((ROOT / 'configs/continuation-v25/protocol.json').read_text())
RUN = PROTOCOL['id']
app = modal.App('mochi-continuation-v25')
volume = modal.Volume.from_name('mochi-continuation-v25-artifacts', create_if_missing=True)
image = (base_image.add_local_dir(ROOT / 'src', '/app/src', copy=True, ignore=['**/__pycache__', '**/*.pyc'])
    .add_local_dir(ROOT / 'configs', '/app/configs', copy=True)
    .add_local_dir(ROOT / 'assets/robot', '/app/assets/robot', copy=True))
mapping = {'physical_attempts': 'physical_rollouts', 'simulation_wall_hours': 'simulation_cpu_hours',
    'inference_input_plus_reserved_output_tokens': 'inference_input_plus_max_output_tokens'}
BOUNDS = {mapping.get(k, k): v for k, v in PROTOCOL['limits'].items()}
# Explicit public API limits for compact semantic records, in addition to writes.
BOUNDS.update(past_ingested_bytes=350000, past_estimated_credits=2000)


@app.function(image=modal.Image.debian_slim(python_version='3.11'), serialized=True,
    cpu=.125, memory=512, max_containers=1, timeout=60, retries=0, volumes={'/artifacts': volume})
def budget(run, transaction, deltas):
    import copy
    from datetime import datetime, timezone
    assert run == RUN
    ledger = modal.Dict.from_name('mochi-continuation-v25-budget', create_if_missing=True)
    state = ledger.get(run)
    if state is None:
        state = {'run_id': run, 'bounds': BOUNDS, 'usage': {k: 0 for k in BOUNDS}, 'transactions': {}}
    assert state['bounds'] == BOUNDS
    if transaction in state['transactions']:
        assert state['transactions'][transaction]['deltas'] == deltas
        return copy.deepcopy(state['usage'])
    for name, amount in deltas.items():
        assert name in BOUNDS and 0 <= state['usage'][name] + amount <= BOUNDS[name], ('Budget ceiling', name)
    for name, amount in deltas.items():
        state['usage'][name] += amount
    state['transactions'][transaction] = {'deltas': deltas, 'at': datetime.now(timezone.utc).isoformat()}
    ledger[run] = state
    directory = Path('/artifacts') / run
    directory.mkdir(exist_ok=True)
    (directory / 'budget.json').write_text(json.dumps(state, indent=2)+'\n')
    volume.commit()
    return copy.deepcopy(state['usage'])


@app.function(image=image, cpu=1, memory=4096, timeout=1200, max_containers=int(os.environ.get('MOCHI_V25_WORKERS','4')),
    retries=0, serialized=True, volumes={'/artifacts': volume})
def trial(layout, seed, action, selection, ident):
    import time
    start = time.perf_counter()
    volume.reload()
    import gzip
    import hashlib
    import platform
    import time
    import torch
    from mochi.navigation_v25.engine import run
    from mochi.smooth_v16.public import rounded
    from mochi.integrations import digest
    torch.set_num_threads(1)
    freeze=Path('/app/configs/continuation-v25/nav-source-freeze.json')
    if freeze.exists():
        for name,expected in json.loads(freeze.read_text())['sha256'].items():
            assert hashlib.sha256((Path('/app')/name).read_bytes()).hexdigest()==expected,name
    directory = Path('/artifacts') / RUN / 'physics'
    directory.mkdir(parents=True, exist_ok=True)
    summary = directory / (ident + '.summary.json')
    request_sha = digest([layout, seed, action, selection])
    assignments=Path('/app/configs/continuation-v25/local-assignments.json')
    assigned=json.loads(assignments.read_text())['identifiers'] if assignments.exists() else []
    waited=time.perf_counter()
    if ident in assigned and not summary.exists():
        try:
            while not summary.exists() and time.perf_counter()-waited<900:
                time.sleep(3)
                volume.reload()
            assert summary.exists(),'Assigned local producer did not finish; never start a competing physical run'
        finally:
            elapsed=time.perf_counter()-waited
            modal.Function.from_name('mochi-continuation-v25','budget').remote(RUN,ident+'-cache-wait',{
                'simulation_cpu_hours':elapsed/3600,'modeled_provider_usd':elapsed*.00002198})
    if summary.exists():
        cached = json.loads(summary.read_text())
        assert cached['request_sha256'] == request_sha
        return cached
    target = directory / (ident + '.json.gz')
    assert not target.exists(), 'Inspect an interrupted export; never overwrite it'
    def choose(observed):
        if selection.get('observation_sha256'):
            assert digest(observed) == selection['observation_sha256']
        return selection
    row = run(layout, seed, action, choose if selection else None, record=True)
    raw = gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1, mtime=0)
    target.write_bytes(raw)
    episode = row['episode']
    public_episode = {k: v for k, v in episode.items() if k not in ['control_telemetry', 'book_motion_samples', 'balance_measurements']}
    public_episode['balance_measurements'] = [{k: v for k, v in m.items() if k in ['t', 'phase', 'roll_rad', 'loads_n', 'step_category']}
        for m in episode['balance_measurements']]
    public_episode['model_decisions'] = episode['decisions']
    public = directory.parent / 'public' / (ident + '.json.gz')
    public.parent.mkdir(exist_ok=True)
    packed = gzip.compress(json.dumps(rounded(public_episode), separators=(',', ':')).encode(), mtime=0)
    public.write_bytes(packed)
    row.update(request_sha256=request_sha,
        artifact={'path': str(target.relative_to('/artifacts')), 'sha256': hashlib.sha256(raw).hexdigest()},
        public_recording={'path': str(public.relative_to('/artifacts')), 'sha256': hashlib.sha256(packed).hexdigest(), 'bytes': len(packed)},
        receipt={'provider': 'Modal', 'cpu': 1, 'memory_mib': 4096, 'duration_seconds': time.perf_counter()-start,
            'architecture': platform.machine(), 'scope': 'Function wall time, including import and export; not an invoice.'},
        balance_metrics=episode['balance_metrics'], loaded_foot_sliding_m=sum(episode['foot_slip_estimate_m'].values()),
        contact_failures=episode['contact_failures'])
    row.pop('episode'); row.pop('tracking')
    summary.write_text(json.dumps(row, indent=2)+'\n')
    volume.commit()
    return row


@app.local_entrypoint()
def initialize():
    usage = modal.Function.from_name('mochi-continuation-v25', 'budget').remote(RUN, 'initialize', {})
    print(json.dumps({'run': RUN, 'usage': usage}))
