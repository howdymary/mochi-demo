"""Reserve new geometric task layouts before selecting a contact repair."""
import copy
import json
from pathlib import Path
import numpy as np
from mochi.navigation_v23.layouts import fingerprint
from mochi.navigation_v25.tasks import TaskWorld
from mochi.navigation_tasks_v24.layouts import articulated_workspace

root=Path(__file__).resolve().parents[1];cfg=root/'configs/laptop-contact-v26'
cfg.mkdir(exist_ok=True)
folder=root/'artifacts/continuation-v25/contact-v26';folder.mkdir(exist_ok=True)
sealed=folder/'sealed-final.json';assert not sealed.exists()
base=json.loads((root/'artifacts/continuation-v25/sequence-native-r3-layout.json').read_text())
candidates=[(.035,-.015,[.29,.06]),(-.035,.020,[-.04,-.245]),(.015,.035,[.28,-.28]),
    (-.025,-.02,[.31,.07]),(.025,.035,[.24,-.26]),(-.035,.035,[.30,.08])]
accepted=[];rejected=[]
for i,(dx,dy,mug) in enumerate(candidates):
    layout=copy.deepcopy(base)
    for p in layout['scene']['props']:
        if p['name'] in ['printer','printer-output-tray','printer-printout']:
            p['pos'][0]+=dx;p['pos'][1]+=dy
        if p['name']=='coffee-mug':p['pos']=[*mug,0.]
    layout['partition']='contact_v26_final';layout['scene']['version']='contact-v26-new-arrangement'
    layout['layout_sha256']=fingerprint({'scene':layout['scene'],'goal':layout['goal']})
    w=TaskWorld(layout,254000)
    try:
        assert articulated_workspace(w)['valid'],'articulated sweep'
        obstacles=w.obstacles();cups=[x for x in obstacles if 'coffee-mug' in (x['name'] or '')]
        for cup in cups:
            for other in obstacles:
                if other in cups:continue
                overlap=np.minimum(cup['maximum'],other['maximum'])-np.maximum(cup['minimum'],other['minimum'])
                assert not all(overlap>.001),'cup AABB overlap with '+str(other['name'])
    except AssertionError as error:
        rejected.append({'candidate':i,'reason':str(error),'dynamic_trials':0});continue
    layout['scope']='New furniture geometry and unopened physics seeds. Same robot, stations, books, fixture mechanics and frozen success checks. No perception claim.'
    layout['static_validation']={'articulated_sweeps_clear':True,'mug_aabb_nonoverlap':True,'dynamic_trials':0}
    accepted.append(layout)
    if len(accepted)==3:break
assert len(accepted)==3
old=json.loads((root/'artifacts/continuation-v25/sealed/final_tasks.json').read_text())
assert not {r['layout_sha256'] for r in accepted}&{r['layout_sha256'] for r in old}
sealed.write_text(json.dumps(accepted,indent=2)+'\n')
dev=json.loads((root/'configs/continuation-v25/tasks/development.json').read_text())[0]
dev['partition']='contact_v26_development';dev['physics_overrides']={'laptop_friction':.075}
(cfg/'development.json').write_text(json.dumps(dev,indent=2)+'\n')
manifest={'id':'mochi-contact26-20261121a','final':{'layouts':3,'physics_seeds':[254000,254001],
    'sha256':fingerprint(accepted),'opened':False},'development':{'physics_seeds':[252000],
    'layout_sha256':dev['layout_sha256'],'declared_hinge_friction_Nm':.075},'geometry_rejections':rejected,
    'weights':'Existing frozen V25 task checkpoint 8 and navigation checkpoint 48; no new optimizer update in this contact-engineering study.',
    'selection':'Choose a contact repair on development physics. Require a qualified continuous development run before opening the new final set. Retain all original V25 final failures.',
    'comparison':'Parent and selected models share the same new source, controller, mechanics and verification. Any controller change is engineering, not a Tinker gain.',
    'limits':'Shares the unchanged V25 512-attempt, 16-summed-wall-hour, 64-optimizer-update and token/spending ledger. Bounded local concurrency at most six.'}
(cfg/'protocol.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'sealed_layouts':3,'set_sha256':manifest['final']['sha256'],'geometry_rejections':len(rejected),'dynamic_trials':0}))
