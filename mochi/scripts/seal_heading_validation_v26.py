"""Prospective selected-model validation; geometric filtering only, no rollouts."""
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import mujoco
import numpy as np
from mochi.navigation_v25.tasks import TaskWorld
from mochi.navigation_v25.kinematic_state_v26 import measured_geometry
from mochi.navigation_v25.heading_approach_v26 import candidate_approach
from mochi.navigation_v25.task_approaches import task_pose
from mochi.navigation_tasks_v24.layouts import articulated_workspace
from mochi.navigation_v23.layouts import fingerprint
from mochi.balanced.sequence import PhysicalStop

root=Path(__file__).resolve().parents[1];directory=root/'artifacts/continuation-v25'
sealed=directory/'contact-v26/sealed-heading-validation.json'
protocol_path=root/'configs/laptop-contact-v26/heading-validation-protocol.json';assert not protocol_path.exists()
prior=json.loads(sealed.read_text()) if sealed.exists() else None
prior_by_hash={row['layout_sha256']:row for row in prior} if prior else {}
source=directory/'contact26-final-0-254000-selected.json.gz'
raw=source.read_bytes();reference=json.loads(gzip.decompress(raw));template,frame,fk_error=measured_geometry(reference)
base=json.loads((directory/'sequence-native-r3-layout.json').read_text())
candidates=[(-.020,.030,[.31,-.26]),(.045,-.010,[.29,.07]),(-.025,.025,[-.06,-.25]),
    (.020,-.025,[.32,.09]),(.035,.015,[.26,-.29]),(-.010,.030,[.30,.08])]
accepted=[];rejected=[]
for index,(dx,dy,mug) in enumerate(candidates):
    layout=copy.deepcopy(base)
    for prop in layout['scene']['props']:
        if prop['name'] in ['printer','printer-output-tray','printer-printout']:
            prop['pos'][0]+=dx;prop['pos'][1]+=dy
        if prop['name']=='coffee-mug':prop['pos']=[*mug,0.]
    layout['partition']='heading_v26_final';layout['scene']['version']='heading-v26-prospective-furniture'
    layout['layout_sha256']=fingerprint({'scene':layout['scene'],'goal':layout['goal']})
    if layout['layout_sha256'] in prior_by_hash:
        accepted.append(prior_by_hash[layout['layout_sha256']])
        if len(accepted)==3:break
        continue
    w=TaskWorld(layout,255000,False)
    try:
        assert articulated_workspace(w)['valid'],'articulated sweep'
        obstacles=w.obstacles();cups=[o for o in obstacles if 'coffee-mug' in (o['name'] or '')]
        for cup in cups:
            for other in obstacles:
                if other in cups:continue
                assert not all(np.minimum(cup['maximum'],other['maximum'])-np.maximum(cup['minimum'],other['minimum'])>.001),'cup AABB overlap'
        for joint in range(w.m.njnt):
            if int(w.m.jnt_bodyid[joint]) not in w.robot_bodies:continue
            address=int(w.m.jnt_qposadr[joint]);size=7 if w.m.jnt_type[joint]==mujoco.mjtJoint.mjJNT_FREE else 1
            w.d.qpos[address:address+size]=template.d.qpos[address:address+size]
        mujoco.mj_forward(w.m,w.d)
        certificate=[]
        for task in ['drawer','laptop','globe']:
            goal=task_pose(w,task);approach=candidate_approach(w,goal)
            certificate.append({'task':task,'goal':goal,'staging':approach,'oriented':hasattr(w,'pending_oriented_approach')})
            if hasattr(w,'pending_oriented_approach'):del w.pending_oriented_approach
            w.d.qpos[:2]=goal[:2];w.d.qpos[3:7]=[math.cos(goal[2]/2),0.,0.,math.sin(goal[2]/2)]
            mujoco.mj_forward(w.m,w.d)
    except (AssertionError,PhysicalStop) as error:
        rejected.append({'candidate':index,'reason':str(error),'dynamic_trials':0});continue
    layout['scope']='Prospective selected-model product validation after shared heading-aware controller engineering. New geometry and physics seed; no new optimizer updates and no claim of a fresh model-weight improvement.'
    layout['static_validation']={'certificate':certificate,'dynamic_trials':0,
        'scope':'Measured robot configuration transferred to planning copies. Original articulated, foot-swing and heading checks. Dynamic execution remains untested.'}
    accepted.append(layout)
    if len(accepted)==3:break
assert len(accepted)==3,{'accepted':len(accepted),'rejections':rejected}
old=json.loads((directory/'contact-v26/sealed-final.json').read_text())
assert not {x['layout_sha256'] for x in accepted}&{x['layout_sha256'] for x in old}
if prior:
    assert fingerprint(accepted)==fingerprint(prior),'Never replace an already sealed cohort'
else:sealed.write_text(json.dumps(accepted,indent=2)+'\n')
protocol={'id':'mochi-heading26-20261121a','final_set_sha256':fingerprint(accepted),'n_layouts':3,
    'physics_seed_by_layout':[255000,255001,255002],'selected_weights':{'navigation':48,'task':8},
    'reference_geometry_sha256':hashlib.sha256(raw).hexdigest(),'reference_fk_error_m':fk_error,
    'geometric_rejections':rejected,'physics_rollouts_during_sealing':0,
    'eligibility':'Require a qualified R3 development run before opening. No further checkpoint selection. This is selected-model product validation, not a paired model-weight study.',
    'limits':'Original 512 physical attempts, 16 summed simulation wall-hours and 64 actual optimizer updates remain unchanged. At most six simultaneous physical workers.'}
protocol['metadata_recovery_without_rollouts']=bool(prior)
protocol_path.write_text(json.dumps(protocol,indent=2)+'\n')
print(json.dumps({'sealed_layouts':len(accepted),'sha256':fingerprint(accepted),'rejected':len(rejected),'physics_rollouts':0}))
