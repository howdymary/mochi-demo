"""Bounded oriented task approaches; original physical collision margins retained."""
import math
import numpy as np
from mochi.balanced.sequence import PhysicalStop
from .task_approaches import candidate_approach as original_approach, pose_corridor_clear
from .planner import plan

def forward_compatible(candidate,goal):
    if candidate['alignment_mode']=='turn_at_goal':return True
    delta=np.asarray(goal[:2])-candidate['pose'][:2]
    if np.linalg.norm(delta)<.001:return True
    error=(math.atan2(delta[1],delta[0])-goal[2]+math.pi)%(2*math.pi)-math.pi
    return abs(error)<=math.radians(15)

def candidate_approach(w,goal):
    try:
        previous=original_approach(w,goal)
    except PhysicalStop as error:
        if str(error)!='no-validated-task-approach':raise
        previous=None
    if previous and forward_compatible(previous,goal):return previous
    forward=np.array([math.cos(goal[2]),math.sin(goal[2])]);lateral=np.array([-forward[1],forward[0]])
    obstacles,envelope=w.obstacles(),w.envelope();choices=[]
    for back in [.02,.03,.04,.06,.08,.12,.16,.20,.24]:
        for side in [0.,.015,-.015,.03,-.03,.06,-.06]:
            point=np.asarray(goal[:2])-back*forward+side*lateral
            if abs(point[0])>.58 or abs(point[1])>.38:continue
            pose=[*point.tolist(),goal[2]]
            feasible=next(((tier,p) for tier,code in enumerate(['planner','buffered','direct']) if (p:=plan(w.d.qpos[:2],pose,obstacles,envelope,code))['feasible']),None)
            if not feasible:continue
            for mode in ['turn_at_goal','fixed_heading']:
                option={'pose':pose,'alignment_mode':mode}
                if not forward_compatible(option,goal):continue
                if pose_corridor_clear(w,pose,goal,mode=='turn_at_goal'):
                    tier,path=feasible
                    choices.append((tier,path['length_m']+back+abs(side),option));break
    if choices:
        chosen=min(choices,key=lambda x:x[:2])[2]
        w.events.append({'t':float(w.d.time),'phase':'forward-compatible-approach-selected','goal':goal,'pose':chosen['pose'],'alignment_mode':chosen['alignment_mode']})
        return chosen
    if previous:return previous
    start=[*w.d.qpos[:2].tolist(),w.yaw()];routes=[]
    # At most 90 two-leg routes. The elbow lies in measured free space, and
    # every heading sweep retains the existing full-body and foot-swing test.
    for x in np.linspace(min(start[0],goal[0])+.05,max(start[0],goal[0])-.005,6):
        for dy in [0.,-.02,.02]:
            for back in [.02,.03,.04,.06,.08]:
                staging=[*(np.asarray(goal[:2])-back*forward).tolist(),goal[2]]
                heading=math.atan2(staging[1]-(start[1]+dy),staging[0]-x)
                elbow=[float(x),start[1]+dy,heading]
                if not pose_corridor_clear(w,start,elbow,True):continue
                if not pose_corridor_clear(w,elbow,staging,True):continue
                if not pose_corridor_clear(w,staging,goal,True):continue
                length=math.dist(start[:2],elbow[:2])+math.dist(elbow[:2],staging[:2])+back
                routes.append((length,[elbow,staging]))
    if not routes:raise PhysicalStop('no-validated-heading-aware-task-approach')
    length,poses=min(routes,key=lambda r:r[0]);w.pending_oriented_approach=poses
    w.events.append({'t':float(w.d.time),'phase':'oriented-task-approach-selected','poses':poses,'length_m':length,
        'source':'Shared geometric fallback, not a learned route decision. No change to collision margins.'})
    return {'pose':poses[-1],'alignment_mode':'turn_at_goal'}
