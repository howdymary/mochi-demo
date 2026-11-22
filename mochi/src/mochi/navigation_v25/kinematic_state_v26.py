"""Reconstruct measured robot geometry for offline planning, never physical replay."""
import math
import mujoco
import numpy as np
from .tasks import TaskWorld

def measured_geometry(row,restore_fixture_state=False):
    episode=row['episode'];frame=episode['trajectory']['frames'][-1]
    names=episode['trajectory']['body_names'];indices={name:i for i,name in enumerate(names)}
    w=TaskWorld(row['layout'],row['seed'],False)
    def matrix(q):
        value=np.empty(9);mujoco.mju_quat2Mat(value,np.asarray(q));return value.reshape(3,3)
    index=indices['pelvis'];w.d.qpos[:3]=frame['positions'][index];w.d.qpos[3:7]=frame['quaternions'][index]
    for joint in range(w.m.njnt):
        body=int(w.m.jnt_bodyid[joint])
        if body not in w.robot_bodies or w.m.jnt_type[joint]!=mujoco.mjtJoint.mjJNT_HINGE:continue
        name=mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,body)
        parent=mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,int(w.m.body_parentid[body]))
        relative=matrix(w.m.body_quat[body]).T@matrix(frame['quaternions'][indices[parent]]).T@matrix(frame['quaternions'][indices[name]])
        skew=np.array([relative[2,1]-relative[1,2],relative[0,2]-relative[2,0],relative[1,0]-relative[0,1]])/2
        w.d.qpos[w.m.jnt_qposadr[joint]]=math.atan2(float(w.m.jnt_axis[joint]@skew),float((np.trace(relative)-1)/2))
    if restore_fixture_state:
        for task,value in frame['objects'].items():
            w.d.qpos[w.q[task]]=math.pi/2-value if task=='laptop' else value
    mujoco.mj_forward(w.m,w.d)
    error=max(float(np.max(np.abs(w.d.xpos[body]-frame['positions'][indices[mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,body)]]))) for body in w.robot_bodies)
    assert error<5e-6,('Recorded FK reconstruction mismatch',error)
    return w,frame,error
