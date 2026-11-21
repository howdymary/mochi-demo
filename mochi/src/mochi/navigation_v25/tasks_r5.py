"""Task-only R5 candidate, following the R3 clearance miss and R4 alignment timeout."""
from . import tasks as r2
from .tasks_r3 import TaskWorld as R3TaskWorld, transit as r3_transit
from .task_lift_r5 import StationSoleFeedbackWalker
from mochi.balanced.onnx_walk import HubWalker

class TaskWorld(R3TaskWorld):
    def step(self,*args,**kwargs):
        if (getattr(self,'station_lift_r5',False) and isinstance(self.walker,HubWalker)
                and not isinstance(self.walker,StationSoleFeedbackWalker)):
            self.walker.__class__=StationSoleFeedbackWalker
        return super().step(*args,**kwargs)

def transit(w,goal,task,*args,**kwargs):
    # Retain the already qualified globe controller; enlarge only the two
    # station-transit residuals implicated by the combined-model preflight.
    w.station_lift_r5=task in ['drawer','laptop']
    try:return r3_transit(w,goal,task,*args,**kwargs)
    finally:w.station_lift_r5=False

def run(*args,**kwargs):
    old_world,old_transit=r2.TaskWorld,r2.transit
    r2.TaskWorld,r2.transit=TaskWorld,transit
    try:return r2.run(*args,**kwargs)
    finally:r2.TaskWorld,r2.transit=old_world,old_transit
