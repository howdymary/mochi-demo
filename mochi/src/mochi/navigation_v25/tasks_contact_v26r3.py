"""R3: oriented approach coverage and a physically settled laptop stance."""
import math
from . import tasks as original
from .tasks_contact_v26r2 import TaskWorld as PriorWorld,transit as prior_transit,policy,finish
from .task_approaches_r9 import transit as station_transit
from .task_approaches import pose_corridor_clear
from .heading_approach_v26 import candidate_approach
from mochi.balanced.onnx_walk import HoldWalker
from mochi.balanced.sequence import PhysicalStop

class TaskWorld(PriorWorld):
    def do_task(self,task,*args,**kwargs):
        if task=='laptop':
            self.phase='pre-contact-supported-settle';self.walker=HoldWalker(self,neutral=True)
            began=float(self.d.time);stable=0.
            while self.d.time-began<2.:
                self.step()
                stable=stable+self.m.opt.timestep if all(self.foot_touching(s) for s in ['left','right']) else 0.
                if stable>=.4:break
            goal=self.station_goal('laptop')
            aligned=math.dist(self.d.qpos[:2],goal[:2])<=.012 and abs((self.yaw()-goal[2]+math.pi)%(2*math.pi)-math.pi)<math.radians(9)
            self.events.append({'t':float(self.d.time),'phase':'pre-laptop-supported-stance','success':stable>=.4 and aligned,'dwell_s':stable,'duration_s':float(self.d.time)-began})
            if stable<.4 or not aligned:raise PhysicalStop('pre-laptop-supported-stance-failed')
        return super().do_task(task,*args,**kwargs)

def transit(w,goal,task,*args,**kwargs):
    poses=getattr(w,'pending_oriented_approach',None)
    if not poses:return prior_transit(w,goal,task,*args,**kwargs)
    del w.pending_oriented_approach
    fine_goal=kwargs.pop('fine_goal',None)
    kwargs.pop('fine_mode',None);kwargs.pop('direct_fine',None)
    arrivals=[]
    for pose in poses+([fine_goal] if fine_goal else []):
        start=[*w.d.qpos[:2].tolist(),w.yaw()]
        if not pose_corridor_clear(w,start,pose,True):raise PhysicalStop('reached-state-oriented-approach-check-failed')
        arrivals.extend(station_transit(w,pose,task,direct_fine=True,fine_mode='turn_at_goal'))
    return arrivals

def run(*args,**kwargs):
    previous=original.TaskWorld,original.transit,original.finish,original.policy,original.candidate_approach
    original.TaskWorld,original.transit,original.finish,original.policy,original.candidate_approach=TaskWorld,transit,finish,policy,candidate_approach
    try:return original.run(*args,**kwargs)
    finally:original.TaskWorld,original.transit,original.finish,original.policy,original.candidate_approach=previous
