"""Purposeful actuator-driven arm clearance before a near-fixture transition."""
import numpy as np
import mujoco
from mochi.balanced.onnx_walk import HoldWalker
from mochi.balanced.sequence import PhysicalStop


def tuck_for_globe(w):
    w.walker = HoldWalker(w)
    w.task, w.phase = None, 'recover'
    arm = w.arm['right']
    start = float(w.d.time)
    origin = w.d.site_xpos[arm['tip']].copy()
    rotation = w.d.xmat[1].reshape(3, 3)
    target = w.d.qpos[:3] + rotation @ np.array([-.020, -.025, -.035])
    normal = np.array([0., 0., 1.])
    next_control, stable = start, 0.
    while w.d.time-start < 5.:
        if w.d.time >= next_control:
            u=float(np.clip((w.d.time-start)/2.,0,1));blend=u**3*(10+u*(-15+6*u))
            point=origin+(target-origin)*blend
            error=point-w.d.site_xpos[arm['tip']]
            error*=min(1.,.0006/max(float(np.linalg.norm(error)),1e-9))
            jac=np.zeros((3,w.m.nv));mujoco.mj_jacSite(w.m,w.d,jac,None,arm['tip'])
            J=jac[:,arm['vs']]
            delta=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,error)
            delta*=min(1.,.025/max(float(np.max(abs(delta))),1e-8))
            w.d.ctrl[arm['acts']]=np.clip(w.d.qpos[arm['qs']]+delta,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
            next_control=float(w.d.time)+.02
        w.step(standing=True)
        good=(np.linalg.norm(w.d.site_xpos[arm['tip']]-target)<.004
            and np.max(abs(w.d.qvel[arm['vs']]))<.10 and all(w.foot_touching(s) for s in ['left','right']))
        stable=stable+w.m.opt.timestep if good else 0.
        if stable>=.25:
            break
    else:
        raise PhysicalStop('globe-clearance-arm-posture-timeout')
    row={'label':'globe-clearance-arm-posture','t':float(w.d.time),'duration_s':float(w.d.time)-start,
        'target':target.tolist(),'actual':w.d.site_xpos[arm['tip']].tolist(),
        'scope':'Shared engineering primitive, not neural training. Joint actuators only; all movement and time count.'}
    w.events.append(row)
    return row
