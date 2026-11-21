"""Open a new cohort only after a qualified uninterrupted development run."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from mochi.navigation_v23.layouts import fingerprint

root = Path(__file__).resolve().parents[1]
directory = root / 'artifacts/continuation-v25'
config = root / 'configs/laptop-contact-v26'
parser = argparse.ArgumentParser()
parser.add_argument('--workers', type=int, default=5)
parser.add_argument('--revision',choices=['contact-v26','contact-v26r2'],default='contact-v26r2')
parser.add_argument('--development-prefix',default='contact26r2-dev')
args = parser.parse_args()
assert 1 <= args.workers <= 6
protocol = json.loads((config / 'protocol.json').read_text())
freeze = config / ('source-freeze-r2.json' if args.revision=='contact-v26r2' else 'source-freeze.json')
for name, expected in json.loads(freeze.read_text())['sha256'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
source_sha = hashlib.sha256(freeze.read_bytes()).hexdigest()
development = [json.loads((directory / f'{args.development_prefix}-{side}.metadata.json').read_text()) for side in ['parent', 'selected']]
assert all(row['status'] == 'completed' and row['source_freeze_sha256'] == source_sha for row in development)
assert development[1]['qualified_complete'], 'Keep final layouts sealed: selected continuous development run must qualify'
sealed = directory / 'contact-v26/sealed-final.json'
layouts = json.loads(sealed.read_text())
assert len(layouts) == 3 and fingerprint(layouts) == protocol['final']['sha256']
marker = directory / 'contact26-final-opened.json'
if not marker.exists():
    marker.write_text(json.dumps({'at': datetime.now(timezone.utc).isoformat(), 'source_freeze_sha256': source_sha,
        'final_set_sha256': fingerprint(layouts), 'development': development,
        'weights': {'parent': {'navigation': 0, 'task': 0}, 'selected': {'navigation': 48, 'task': 8}},
        'scope': 'New final cohort after original V25 task-final laptop failures. Controller engineering shared by both sides. No final outcomes used as labels. Native gait fixed.'}, indent=2) + '\n')
else:
    saved = json.loads(marker.read_text())
    assert saved['source_freeze_sha256'] == source_sha and saved['final_set_sha256'] == fingerprint(layouts)
jobs = []
for index, layout in enumerate(layouts):
    path = directory / f'contact26-final-layout-{index}.json'
    raw = json.dumps(layout, indent=2) + '\n'
    if path.exists():
        assert path.read_text() == raw
    else:
        path.write_text(raw)
    for seed in protocol['final']['physics_seeds']:
        for side, nav, task in [('parent', 0, 0), ('selected', 48, 8)]:
            jobs.append((f'contact26-final-{index}-{seed}-{side}', path, seed,
                {'navigation': {'mode': 'tinker', 'representation': 'compact', 'update': nav}, 'task': {'update': task}}))

def attempt(job):
    ident, layout, seed, settings = job
    policy = directory / (ident + '-policy.json')
    raw = json.dumps(settings, indent=2) + '\n'
    if policy.exists():
        assert policy.read_text() == raw
    else:
        policy.write_text(raw)
    metadata = directory / (ident + '.metadata.json')
    if not metadata.exists():
        command = [sys.executable, str(root / 'scripts/probe_sequence_v25.py'), '--id', ident,
            '--seed', str(seed), '--layout', str(layout), '--policy-config', str(policy),
            '--engineering-revision', args.revision]
        with (directory / (ident + '.log')).open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                env={**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'})
        assert result.returncode == 0, (ident, 'Incomplete attempt retained; do not overwrite')
    row = json.loads(metadata.read_text())
    assert row['status'] == 'completed' and row['source_freeze_sha256'] == source_sha
    row['request_sha256'] = fingerprint([json.loads(layout.read_text()), seed, settings, source_sha])
    print(json.dumps({k: row[k] for k in ['id', 'qualified_complete', 'complete_sequence_success', 'failure', 'steps', 'physical_seconds']}), flush=True)
    return row

output = directory / 'contact26-final-continuous.json'
assert not output.exists(), 'Preserve completed cohort'
with ThreadPoolExecutor(max_workers=args.workers) as pool:
    results = list(pool.map(attempt, jobs))
output.write_text(json.dumps({'phase': 'final', 'results': results, 'engineering_revision': args.revision,
    'physical_source_sha256': source_sha, 'final_set_sha256': fingerprint(layouts),
    'scope': 'Three new layouts, two new seeds, two frozen model sides. Identical shared source and verification. Every attempted layout retained.'}, indent=2) + '\n')
