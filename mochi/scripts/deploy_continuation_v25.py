"""A separate read-only replay deployment; prior demonstrations stay intact."""
import json
import os
from pathlib import Path
import modal

root=Path(__file__).resolve().parents[1]
web=root/'web/desk'
manifest=json.loads((web/'continuation-v25/manifest.json').read_text())
assert manifest['checkpoints'] and manifest['totals'][0][0]>0
image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1').env({'MOCHI_RELEASE':os.environ.get('MOCHI_RELEASE','local')})
files=['showcase-v27.html','continuation-v25.html','continuation-v25.js','navigation-v23.css','navigation-v23-stage.js','navigation-v23-renderer.js',
    'visual-motion-v22.css','visual-v22-stage.js','g1-v22-stage.js','realism-v22.js','efficient-evidence.mjs','vintage-clock.js','richdesk-stage.js']
for name in files:image=image.add_local_file(web/name,'/web/'+name,copy=True)
image=(image.add_local_file(web/'showcase-v27.html','/web/index.html',copy=True)
    .add_local_file(web/'showcase-v27/manifest.json','/web/showcase-v27/manifest.json',copy=True)
    .add_local_dir(web/'assets','/web/assets',copy=True)
    .add_local_dir(web/'continuation-v25','/web/continuation-v25',copy=True,ignore=['*.json.gz']))
app=modal.App('mochi-continuation-v25-demo')
volume=modal.Volume.from_name('mochi-continuation-v25-artifacts')


@app.function(image=image,serialized=True,cpu=.25,memory=512,max_containers=2,scaledown_window=120,
    volumes={'/recordings':volume.with_mount_options(read_only=True,sub_path='/'+manifest['run_id']+'/public')})
@modal.asgi_app()
def web():
    from functools import lru_cache
    import hashlib
    from fastapi import FastAPI,HTTPException
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    api=FastAPI();api.add_middleware(GZipMiddleware,minimum_size=1000)
    report=json.loads(Path('/web/continuation-v25/manifest.json').read_text())
    showcase=json.loads(Path('/web/showcase-v27/manifest.json').read_text())
    @lru_cache(maxsize=12)
    def video(name):
        entry=showcase['files'].get(name)
        if not entry:raise HTTPException(404)
        path=Path('/recordings/showcase-v27')/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise HTTPException(503,'Video integrity check failed')
        return path
    @api.get('/showcase-v27/{name}')
    def showcase_artifact(name:str):
        if name=='manifest.json':
            return FileResponse('/web/showcase-v27/manifest.json',media_type='application/json',headers={'Cache-Control':'no-cache'})
        content_type='video/mp4' if name.endswith('.mp4') else 'image/jpeg'
        return FileResponse(video(name),media_type=content_type,headers={'Cache-Control':'public,max-age=3600','Content-Encoding':'identity'})
    @lru_cache(maxsize=512)
    def recording(name):
        entry=report['recordings'].get(name)
        if not entry:raise HTTPException(404)
        path=Path('/recordings')/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise HTTPException(503,'Recording integrity check failed')
        return path
    @api.get('/continuation-v25/{name}')
    def artifact(name:str):
        if name.endswith('.json.gz'):
            return FileResponse(recording(name),media_type='application/gzip',headers={'Cache-Control':'public,max-age=31536000,immutable'})
        if name!='manifest.json':raise HTTPException(404)
        return FileResponse('/web/continuation-v25/manifest.json',media_type='application/json',headers={'Cache-Control':'no-cache'})
    @api.get('/api/health')
    def health():
        navigation=max((c['update'] for c in report['checkpoints'] if c['domain']=='navigation'),default=0)
        task=max((c['update'] for c in report['checkpoints'] if c['domain']=='task and recovery'),default=0)
        return {'status':'ok','release':os.getenv('MOCHI_RELEASE'),'run_id':report['run_id'],
            'evaluation_status':report['status'],'optimizer_updates':navigation+task,
            'navigation_optimizer_updates':navigation,'task_optimizer_updates':task,
            'cases':len(report['cases']),'native_gait_weights_trained':False,'privileged_state':True,
            'showcase_videos':3,'showcase_final_steps':showcase['final']['steps'],
            'mode':'Three recorded simulation videos; detailed experiment viewer preserved'}
    api.mount('/',StaticFiles(directory='/web',html=True))
    return api
