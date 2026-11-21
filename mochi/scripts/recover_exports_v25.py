"""Finish interrupted artifact exports without rerunning completed physics."""
import json
from pathlib import Path
import modal
from mochi.navigation_v25.remote import image,volume,RUN

app=modal.App('mochi-continuation-v25-export-recovery')
@app.function(image=image,serialized=True,cpu=1,memory=4096,timeout=600,retries=0,volumes={'/artifacts':volume})
def recover():
    import gzip
    import hashlib
    import platform
    import time
    from mochi.smooth_v16.public import rounded
    volume.reload();directory=Path('/artifacts')/RUN
    archived=directory/'diagnostics/navigation-before-export-recovery.json'
    assert not archived.exists();archived.write_bytes((directory/'navigation-training.json').read_bytes())
    repaired=[]
    for raw_path in sorted((directory/'physics').glob('dev-*.json.gz')):
        ident=raw_path.name[:-8];summary=raw_path.with_name(ident+'.summary.json')
        if summary.exists():continue
        started=time.perf_counter();raw=raw_path.read_bytes();row=json.loads(gzip.decompress(raw))
        assert all(k in row for k in ['episode','qualified','checks','selection','initial_physical_state_sha256'])
        episode=row['episode']
        clip={k:v for k,v in episode.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
        clip['balance_measurements']=[{k:v for k,v in m.items() if k in ['t','phase','roll_rad','loads_n','step_category']} for m in episode['balance_measurements']]
        clip['model_decisions']=episode['decisions']
        packed=gzip.compress(json.dumps(rounded(clip),separators=(',',':')).encode(),mtime=0)
        public=directory/'public'/(ident+'-recovered.json.gz');assert not public.exists();public.write_bytes(packed)
        row.update(request_sha256=__import__('mochi.integrations',fromlist=['digest']).digest([row['layout'],row['seed'],row['action'],row['selection']]),
            artifact={'path':str(raw_path.relative_to('/artifacts')),'sha256':hashlib.sha256(raw).hexdigest()},
            public_recording={'path':str(public.relative_to('/artifacts')),'sha256':hashlib.sha256(packed).hexdigest(),'bytes':len(packed)},
            receipt={'provider':'Modal','cpu':1,'memory_mib':4096,'duration_seconds':360.,'architecture':platform.machine(),
                'scope':'Conservative original 360-second reservation. Function-end timing was interrupted during export; no invented actual-duration refund.',
                'known_engine_wall_seconds':row['wall_seconds'],'recovery_export_seconds':time.perf_counter()-started},
            balance_metrics=episode['balance_metrics'],loaded_foot_sliding_m=sum(episode['foot_slip_estimate_m'].values()),contact_failures=episode['contact_failures'])
        row['export_recovery']={'physics_repeated':False,'original_raw_sha256':hashlib.sha256(raw).hexdigest(),'partial_exports_overwritten':False}
        row.pop('episode');row.pop('tracking')
        with summary.open('x') as out:out.write(json.dumps(row,indent=2)+'\n')
        repaired.append({'id':ident,'qualified':row['qualified'],'raw_sha256':row['artifact']['sha256']})
    report={'repaired':repaired,'physical_rollouts_in_recovery':0,'optimizer_updates_in_recovery':0,
        'scope':'Reconstructed only from complete, parseable authoritative raw episodes. Original raw and any partial public files are preserved.'}
    (directory/'export-recovery-r3.json').write_text(json.dumps(report,indent=2)+'\n');volume.commit();return report

@app.local_entrypoint()
def main():
    result=recover.remote();root=Path(__file__).resolve().parents[1]
    (root/'artifacts/continuation-v25/export-recovery-r3.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
