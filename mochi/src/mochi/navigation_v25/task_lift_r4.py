"""R4 task-only candidate: larger bounded pad-clearance targets, fixed gait."""
import math
import mujoco
import numpy as np

from mochi.balanced.onnx_walk import HubWalker
from .task_lift import SoleFeedbackWalker


class StationSoleFeedbackWalker(SoleFeedbackWalker):
    """Fixed native policy plus a shared, contact-gated engineering residual.

    The older residual raises a foot-centre reference without controlling sole
    tilt. Here every collision pad contributes a vertical error, retaining
    native horizontal swing and the original actuator force limits.
    """
    def command(self,velocity):
        HubWalker.command(self,velocity)
        if not hasattr(self,'sole_started'):
            self.sole_started={s:None for s in ['left','right']}
            self.sole_delta={s:np.zeros(6) for s in self.sole_started}
            self.sole_last=float(self.d.time);self.sole_calls=0
        dt=max(0.,min(.01,float(self.d.time)-self.sole_last));self.sole_last=float(self.d.time)
        moving=self.mode=='walk' and (np.linalg.norm(velocity[:2])>=.015 or abs(velocity[2])>=.20)
        loads=self.w.loads()
        turning=abs(velocity[2])>=.20
        peak=.012 if turning else .010
        cap=.006 if turning else .005
        limit=.16 if turning else .14
        rate=3.0 if turning else 2.5
        for i,side in enumerate(['left','right']):
            other='right' if side=='left' else 'left';requested=np.zeros(6)
            if not moving or loads[side]>.20:self.sole_started[side]=None
            elif loads[other]>=.65:
                if self.sole_started[side] is None:self.sole_started[side]=float(self.d.time)
                u=(float(self.d.time)-self.sole_started[side])/.12
                if 0<u<1:
                    target=peak*math.sin(math.pi*u)**2
                    body=self.w.id('body',side+'_ankle_roll_link')
                    point=self.d.xpos[body]+self.d.xmat[body].reshape(3,3)@np.array([.0058,0,-.00585])
                    J=np.zeros((3,self.m.nv));mujoco.mj_jac(self.m,self.d,J,None,point,body)
                    vs=self.vids[i*6:(i+1)*6]
                    rows=[J[0,vs],J[1,vs]];errors=[0.,0.]
                    for gid in self.w._foot_geoms[side]:
                        position=self.d.geom_xpos[gid]
                        clearance=float(position[2]-self.m.geom_size[gid,0]-self.w.terrain_height(*position[:2]))
                        mujoco.mj_jac(self.m,self.d,J,None,position,body)
                        rows.append(J[2,vs].copy())
                        errors.append(float(np.clip(target-clearance,-cap,cap)))
                    A=np.asarray(rows);error=np.asarray(errors)
                    requested=np.linalg.solve(A.T@A+np.eye(6)*1e-7,A.T@error)
                    requested=np.clip(requested,-limit,limit);self.sole_calls+=1
            self.sole_delta[side]+=np.clip(requested-self.sole_delta[side],-rate*dt,rate*dt)
            for j,actuator in enumerate(self.aids[i*6:(i+1)*6]):
                index=self.amap.index(int(actuator))
                self.d.ctrl[actuator]=np.clip(self.d.ctrl[actuator]+self.kp[index]*self.sole_delta[side][j],*self.m.actuator_forcerange[actuator])

    def description(self):
        return {**HubWalker.description(self),'sole_clearance_feedback':{'turn_peak_m':.012,'straight_peak_m':.010,
            'max_pad_position_error_m':.006,'max_joint_residual_rad':.16,'joint_reference_rate_rad_s':3.0,
            'contact_gated':True,'calls':getattr(self,'sole_calls',0),'weights_trained':False}}
