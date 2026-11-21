"""A small, predeclared contact-control pilot with unopened furniture layouts."""
import copy
import json
from pathlib import Path
import numpy as np

from mochi.navigation_v23.layouts import fingerprint
from mochi.navigation_v25.tasks import TaskWorld
from mochi.navigation_tasks_v24.layouts import articulated_workspace

root=Path(__file__).resolve().parents[1]
folder=root/'configs/continuation-v25/tasks';folder.mkdir(exist_ok=True)
sealed=root/'artifacts/continuation-v25/sealed/final_tasks.json'
assert not sealed.exists()
base=json.loads((root/'artifacts/continuation-v25/sequence-native-r3-layout.json').read_text())


def arrangement(dx,dy,mug,partition):
    layout=copy.deepcopy(base)
    for p in layout['scene']['props']:
        if p['name'] in ['printer','printer-output-tray','printer-printout']:
            p['pos'][0]+=dx;p['pos'][1]+=dy
        if p['name']=='coffee-mug':p['pos']=[*mug,0.]
    layout['partition']=partition
    layout['scene']['version']='navigation-tasks-v25-globe-workspace-r2'
    layout['scope']='Task-control pilot. New printer/cup arrangements; fixed 8 mm book geometry, station locations, mechanics and success checks. Exact state information.'
    layout['layout_sha256']=fingerprint({'scene':layout['scene'],'goal':layout['goal']})
    w=TaskWorld(layout,253000)
    assert articulated_workspace(w)['valid']
    obstacles=w.obstacles();cups=[x for x in obstacles if 'coffee-mug' in (x['name'] or '')]
    for cup in cups:
        for other in obstacles:
            if other in cups:continue
            overlap=np.minimum(cup['maximum'],other['maximum'])-np.maximum(cup['minimum'],other['minimum'])
            assert not all(overlap>.001),(partition,other['name'])
    layout['static_validation']={'articulated_sweeps_clear':True,'mug_aabb_nonoverlap':True,'dynamic_trials':0}
    return layout


training=[arrangement(0,0,[.06654724244008654,.11571246037612037],'task_training')]
development=[arrangement(.01,-.02,[.33,.10],'task_development')]
final=[arrangement(-.025,0,[.30,.09],'task_final'),arrangement(.03,.02,[-.01,-.29],'task_final'),arrangement(-.015,.025,[.26,-.29],'task_final')]
for name,layouts in [('training',training),('development',development)]:
    p=folder/(name+'.json');assert not p.exists();p.write_text(json.dumps(layouts,indent=2)+'\n')
sealed.write_text(json.dumps(final,indent=2)+'\n')
manifest={'training':{'layouts':1,'physics_seeds':[231000,231001],'sha256':fingerprint(training)},
    'development':{'layouts':1,'physics_seeds':[252000],'sha256':fingerprint(development)},
    'final':{'layouts':3,'physics_seeds':[253000,253001],'sha256':fingerprint(final),'opened':False},
    'scope':'Small task-control pilot: every declared final arrangement is evaluated under both seeds. Separate from the eight-layout final navigation cohort and the earlier unopened V23 sequence cohort.',
    'selection':'Train on reached component states from two training physics seeds; select on measured alternatives in a separate development arrangement. Validate parent and selected weights in new continuous final attempts.'}
(folder/'splits.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='selection'}),flush=True)
