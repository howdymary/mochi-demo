"""Archive exact physical records without exposing backend credentials or states."""
import hashlib
import json
from pathlib import Path
import modal

root = Path(__file__).resolve().parents[1]
directory = root / 'artifacts/continuation-v25'
assert (directory / 'contact26-final-continuous.json').exists(), 'Archive the completed cohort together'
run = 'mochi-nav25-20261121a'
volume = modal.Volume.from_name('mochi-continuation-v25-artifacts')
patterns = ['task-final-*-*-*.json.gz', 'contact26*-dev-*.json.gz',
    'contact26-final-*-*-*.json.gz', 'laptop-development-*.json.gz', 'laptop-original-state-*.json.gz']
files = sorted({path for pattern in patterns for path in directory.glob(pattern)})
rows = []
uploads = []
for path in files:
    assert path.name.endswith('.json.gz') and not path.name.startswith(('private', 'public'))
    with path.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    remote = run + '/contact-continuation/raw/' + path.name
    rows.append({'file': path.name, 'path': remote, 'sha256': sha, 'bytes': path.stat().st_size})
    uploads.append((path, '/' + remote))
    metadata = path.with_name(path.name[:-8] + '.metadata.json')
    assert metadata.exists(), metadata.name
    uploads.append((metadata, '/' + run + '/contact-continuation/raw/' + metadata.name))
with volume.batch_upload() as batch:
    for path, remote in uploads:
        batch.put_file(path, remote)
report = {'volume': 'mochi-continuation-v25-artifacts', 'records': rows,
    'scope': 'Exact full physical records and companion metadata. Public replay files are separate. No pickle snapshots, model-state paths, logs or credentials are included.'}
target = root / 'evidence/continuation-v25/contact-raw-artifacts.json'
assert not target.exists()
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'physical_records_archived': len(rows), 'total_bytes': sum(row['bytes'] for row in rows)}))
