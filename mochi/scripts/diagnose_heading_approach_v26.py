"""A bounded orientation-aware corridor search on measured geometry only."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from mochi.navigation_v25.kinematic_state_v26 import measured_geometry
from mochi.navigation_v25.task_approaches import pose_corridor_clear
from mochi.navigation_v25.planner import clearance

root=Path(__file__).resolve().parents[1]
source=root/'artifacts/continuation-v25/contact26-final-0-254000-selected.json.gz'
raw=source.read_bytes();row=json.loads(gzip.decompress(raw));w,frame,error=measured_geometry(row)
start=[*w.d.qpos[:2].tolist(),w.yaw()];goal=w.station_goal('drawer')
obstacles=w.obstacles();near=sorted([{'name':o['name'],'distance_m':float(clearance(start[:2],[o])[0])} for o in obstacles],key=lambda x:x['distance_m'])[:8]
routes=[];tested=0
for x in [-.215,-.205,-.195,-.185,-.175,-.165]:
    for dy in [0.,-.02,.02]:
        for back in [.02,.03,.04,.06,.08]:
            staging=[goal[0],goal[1]-back,goal[2]]
            heading=math.atan2(staging[1]-(start[1]+dy),staging[0]-x)
            elbow=[x,start[1]+dy,heading];tested+=1
            if not pose_corridor_clear(w,start,elbow,True):continue
            if not pose_corridor_clear(w,elbow,staging,True):continue
            if not pose_corridor_clear(w,staging,goal,True):continue
            routes.append({'poses':[elbow,staging,goal],
                'length_m':math.dist(start[:2],elbow[:2])+math.dist(elbow[:2],staging[:2])+math.dist(staging[:2],goal[:2])})
routes.sort(key=lambda x:x['length_m'])
result={'source_sha256':hashlib.sha256(raw).hexdigest(),'frame_t':frame['t'],'maximum_robot_fk_error_m':error,
    'start':start,'goal':goal,'envelope':w.envelope(),'nearest_start_obstacles':near,'tested_routes':tested,
    'feasible_routes':routes,'physics_steps':0,
    'scope':'Geometry-only analysis of an opened cohort, for a later engineering candidate. Actual measured robot body transforms reconstruct to the stated FK error. Fixture initialization uses the original seed. No physical rollout, policy training or trajectory modification. Every route retains the original full-body, foot-swing and heading-sweep checks.'}
out=root/'evidence/continuation-v25/heading-approach-diagnosis.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'feasible_routes':len(routes),'tested':tested,'best':routes[0] if routes else None,'start_clearance':near[:2],'planning_radius':w.envelope()['planning_radius_m'],'physics_steps':0}))
