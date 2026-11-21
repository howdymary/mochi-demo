"""Generate distinct layouts using geometry only; final coordinates stay private."""
import copy
import json
from pathlib import Path
import numpy as np

from mochi.navigation_v23.layouts import generate, fingerprint
from mochi.navigation_v25.engine import inspect

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'configs/continuation-v25'
PRIVATE = ROOT / 'artifacts/continuation-v25/sealed'
PRIVATE.mkdir(exist_ok=True)
manifest = {}
for partition, count, base, shift in [('training', 40, 261000, 0), ('development', 8, 262000, 1), ('final_navigation', 8, 263000, 2)]:
    target = (PRIVATE if partition.startswith('final') else PUBLIC) / (partition+'.json')
    assert not target.exists(), 'Never overwrite a sealed cohort'
    accepted, rejected, families = [], [], [0]*4
    for index in range(2000):
        family = index % 4
        if families[family] >= count//4:
            continue
        seed = base + index*101
        layout = generate(seed, 'training', index)
        rng = np.random.default_rng(seed+501)
        scene = layout['scene']
        scene['version'] = 'navigation-v25-full-initial-state'
        printer=next(p for p in scene['props'] if p['name']=='printer')
        if family==1:
            for prop in scene['props']:
                if prop['name'] in ['printer','printer-output-tray','printer-printout']:
                    prop['pos'][1]+=.07
        family_mug = (family+shift)%4
        # Keep the cup outside the printer/tray assembly while changing which
        # side of that assembly blocks the route. Validation still rejects
        # overlaps with any other fixture, before any dynamic test.
        centre = [[printer['pos'][0]+.22,.075],[printer['pos'][0]-.22,-.17],
            [printer['pos'][0]-.22,.09],[printer['pos'][0]+.22,-.18]][family_mug]
        for prop in scene['props']:
            if prop['name']=='coffee-mug':
                prop['pos']=[centre[0]+float(rng.uniform(-.012,.012)),centre[1]+float(rng.uniform(-.012,.012)),0.]
        if family_mug==3:
            layout['goal'][1]=float(rng.uniform(.06,.11))
        # The goal-heading combination is independent of the corridor family.
        headings = [0., np.pi/2, -np.pi/2]
        layout['goal'][2] = float(headings[(index//4+shift)%3])
        layout.update(partition=partition, generation_seed=seed,
            scope='V25 flat navigation. Full sampled physical initialization; shared arm-holding and direction-preserving alignment. No perception or native gait training.')
        layout['layout_sha256'] = fingerprint({'scene':scene,'goal':layout['goal']})
        reasons=[]
        for physics_seed in [251000,251001]:
            w,envelope,obstacles,plans=inspect(layout,physics_seed)
            reasons.extend(f'{physics_seed}:{a}:{p.get("reason")}' for a,p in plans.items() if not p['feasible'])
            mugs=[o for o in obstacles if 'coffee-mug' in (o['name'] or '')]
            for mug in mugs:
                for other in obstacles:
                    if 'coffee-mug' in (other['name'] or ''):
                        continue
                    overlap=np.minimum(mug['maximum'],other['maximum'])-np.maximum(mug['minimum'],other['minimum'])
                    if all(overlap>.001):
                        reasons.append('mug-overlap:'+str(other['name']))
        if reasons:
            rejected.append({'generation_seed':seed,'sha256':layout['layout_sha256'],'reasons':sorted(set(reasons))})
            continue
        layout['geometric_validation']={'both_physics_seed_resets_checked':True,
            'all_profiles_feasible':True,'physics_rollouts_executed':0,'family':family,
            'scope':'Static geometry only. No model, training labels, reward or dynamic outcome used for cohort filtering.'}
        accepted.append(copy.deepcopy(layout));families[family]+=1
        if len(accepted)%8==0:
            print(partition,len(accepted),'geometrically accepted',flush=True)
        if len(accepted)==count:
            break
    (ROOT/'artifacts/continuation-v25'/f'{partition}-rejections.json').write_text(json.dumps(rejected,indent=2)+'\n')
    assert len(accepted)==count,(partition,families)
    target.write_text(json.dumps(accepted,indent=2)+'\n')
    manifest[partition]={'count':count,'sha256':fingerprint(accepted),'family_counts':families,
        'static_rejections':len(rejected),'path':str(target.relative_to(ROOT))}
    print(partition,count,'sealed; static rejections',len(rejected),flush=True)
(PUBLIC/'navigation-splits.json').write_text(json.dumps(manifest,indent=2)+'\n')
