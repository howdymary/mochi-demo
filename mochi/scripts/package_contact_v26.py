"""Publish full contact-continuation recordings, including failed attempts."""
import gzip
import hashlib
import json
from pathlib import Path
import modal
from mochi.smooth_v16.public import rounded

root = Path(__file__).resolve().parents[1]
directory = root / 'artifacts/continuation-v25'
target = root / 'web/desk/continuation-v25/manifest.json'
manifest = json.loads(target.read_text())
run = manifest['run_id']
volume = modal.Volume.from_name('mochi-continuation-v25-artifacts')
training = json.loads(b''.join(volume.read_file(run + '/task-training.json')))
uploads = []
cohort_file = directory / 'contact26-final-continuous.json'
cohort = json.loads(cohort_file.read_text()) if cohort_file.exists() else None
manifest.setdefault('claim_before_contact_continuation',manifest['claim'])
manifest['claim']=manifest['claim_before_contact_continuation']
manifest['cases'] = [c for c in manifest['cases'] if not c['id'].startswith('contact26-')]
manifest['results'] = [r for r in manifest['results'] if r['cohort'] != 'Fresh four-task contact continuation']

def recording(metadata, label):
    raw = (directory / (metadata['id'] + '.json.gz')).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == metadata['sha256']
    row = json.loads(gzip.decompress(raw))
    episode = row['episode']
    public = {k: v for k, v in episode.items() if k not in ['control_telemetry', 'book_motion_samples', 'balance_measurements']}
    public['balance_measurements'] = [{k: v for k, v in r.items() if k in ['t', 'phase', 'roll_rad', 'loads_n', 'step_category']} for r in episode['balance_measurements']]
    public['model_decisions'] = episode['decisions']
    packed = gzip.compress(json.dumps(rounded(public), separators=(',', ':')).encode(), mtime=0)
    name = metadata['id'] + '.json.gz'
    path = directory / ('public-' + name)
    if path.exists():
        assert path.read_bytes() == packed
    else:
        path.write_bytes(packed)
    sha = hashlib.sha256(packed).hexdigest()
    if name not in manifest['recordings']:
        uploads.append((path, '/' + run + '/public/' + name))
    else:
        assert manifest['recordings'][name]['sha256']==sha
    manifest['recordings'][name] = {'path': run + '/public/' + name, 'sha256': sha, 'bytes': len(packed)}
    settings = metadata['policy_settings']
    update = settings['task']['update']
    checkpoint = next(c for c in training['checkpoints'] if c['update'] == update)
    nav = settings['navigation']['update']
    return {'file': name, 'sha256': sha, 'label': label, 'updates': f'navigation {nav}; task {update}',
        'row': {'kind': 'sequence', 'qualified_complete': row['qualified_complete'], 'steps': metadata['steps'],
            'duration': metadata['physical_seconds'], 'failure': row['failure'],
            'action': f'navigation {nav}; task checkpoint {update}',
            'selection': {'checkpoint_id': checkpoint['checkpoint_id'], 'optimizer_updates': f'nav {nav}, task {update}'},
            'checkpoint_decisions': metadata['checkpoint_decisions']}}

def add_case(ident, label, split, rows):
    assert len(rows) == 2 and rows[0]['layout_sha256'] == rows[1]['layout_sha256']
    runs = {}
    for row in rows:
        side = row['id'].rsplit('-', 1)[1]
        runs[side] = recording(row, 'Parent models' if side == 'parent' else 'Selected models')
    case = {'id': ident, 'label': label, 'kind': 'sequence', 'split': split,
        'layout_sha256': rows[0]['layout_sha256'], 'runs': runs,
        'scope': 'One uninterrupted actuator-driven clock, drawer, laptop and globe attempt per side. Identical scene, reset, '+rows[0]['engineering_revision']+' controller and unchanged quality checks. Both models use privileged state. Native gait fixed.',
        'comparison_note': 'Controller repairs are shared engineering changes. Only saved selection-model weights differ within this pair. The full cohort, failures and earlier negative task cohort remain available.'}
    manifest['cases'].append(case)
    return case

development_history=[]
for prefix in ['contact26','contact26r2']:
    paths=[directory/f'{prefix}-dev-{side}.metadata.json' for side in ['parent','selected']]
    if all(p.exists() for p in paths):
        development=[json.loads(p.read_text()) for p in paths]
        add_case(prefix.replace('contact26r2','contact26-r2')+'-development',prefix+' · continuous development','development',development)
        development_history.append(development)
assert development_history
development=development_history[-1]
if cohort:
    assert len(cohort['results']) == 12
    for i in range(3):
        for seed in [254000, 254001]:
            pair = [r for r in cohort['results'] if r['id'].startswith(f'contact26-final-{i}-{seed}-')]
            add_case(f'contact26-final-{i}-{seed}', f'Contact continuation · fresh layout {i+1} · seed {seed}', 'final', pair)
    for side in ['parent', 'selected']:
        rows = [r for r in cohort['results'] if r['id'].endswith('-' + side)]
        good = [r for r in rows if r['qualified_complete']]
        manifest['results'].append({'cohort': 'Fresh four-task contact continuation', 'method': side.title() + ' models',
            'qualified': len(good), 'n': len(rows), 'mean_steps': sum(r['steps'] for r in good) / len(good) if good else None})
    selected = [r for r in cohort['results'] if r['id'].endswith('-selected')]
    n = sum(r['qualified_complete'] for r in selected)
    manifest['contact_continuation'] = {'qualified_final': n, 'n_final': 6, 'source_sha256': cohort['physical_source_sha256'],
        'scope': 'New final set after the original task-final failure; same saved weights, revised shared controller. No extra optimizer updates.'}
    manifest['claim'] += f' The separate contact continuation qualified on {n}/6 selected-model attempts across three new layouts.'
    eligible = [c for c in manifest['cases'] if c['id'].startswith('contact26-final-') and c['runs']['selected']['row']['qualified_complete']]
    if eligible:
        chosen = eligible[0]
        chosen['label'] += ' · post-evaluation highlight'
        chosen['comparison_note'] += ' This opening example was selected after evaluation; use the cohort table to assess reliability.'
        manifest['default_case'] = chosen['id']
else:
    manifest['contact_continuation'] = {'final_opened': (directory / 'contact26-final-opened.json').exists(),
        'development_qualified': development[1]['qualified_complete'], 'scope': 'Development only; no fresh complete-sequence claim.'}
    if development[1]['qualified_complete']:
        manifest['default_case']='contact26-r2-development'

for query in manifest['sources']:
    for source in query['sources']:
        if source.get('excerpt'):
            source['excerpt'] = ' '.join(source['excerpt'].split()[:10])
usage = modal.Dict.from_name('mochi-continuation-v25-budget')[run]['usage']
for total in manifest['totals']:
    if total[1] == 'charged physical attempts':
        total[0] = usage['physical_rollouts']
manifest['execution'] = f'{usage["physical_rollouts"]} charged physical attempts; {usage["simulation_cpu_hours"]:.2f} summed simulation wall hours at this snapshot. Actual optimizer updates remain 64. Costs are modeled, not invoices.'
with volume.batch_upload() as batch:
    for path, destination in uploads:
        batch.put_file(path, destination)
target.write_text(json.dumps(manifest, separators=(',', ':')) + '\n')
evidence = root / 'evidence/continuation-v25'
(evidence / 'contact-continuation-results.json').write_text(json.dumps({'development': development, 'development_history':development_history,'final': cohort, 'usage': usage}, indent=2) + '\n')
print(json.dumps({'cases': len(manifest['cases']), 'contact_continuation': manifest['contact_continuation']}))
