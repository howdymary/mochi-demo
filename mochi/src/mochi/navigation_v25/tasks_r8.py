"""R8: leg-torque filtering and a physically verified final supported stance."""
from . import tasks as r2
from .tasks_r5 import TaskWorld as R5World
from .task_approaches import transit as base_transit
from .task_lift_r8 import FilteredStationWalker
from .tasks_r7 import finish
from mochi.balanced.onnx_walk import HubWalker

class TaskWorld(R5World):
    def step(self,*args,**kwargs):
        if (getattr(self,'station_torque_filter',False) and isinstance(self.walker,HubWalker)
                and not isinstance(self.walker,FilteredStationWalker)):
            self.walker.__class__=FilteredStationWalker
        return super().step(*args,**kwargs)

def transit(w,goal,task,*args,**kwargs):
    w.station_lift_r5=task in ['drawer','laptop'];w.station_torque_filter=w.station_lift_r5
    try:return base_transit(w,goal,task,*args,**kwargs)
    finally:w.station_lift_r5=False;w.station_torque_filter=False

def run(*args,**kwargs):
    old_world,old_transit,old_finish=r2.TaskWorld,r2.transit,r2.finish
    r2.TaskWorld,r2.transit,r2.finish=TaskWorld,transit,finish
    try:return r2.run(*args,**kwargs)
    finally:r2.TaskWorld,r2.transit,r2.finish=old_world,old_transit,old_finish
