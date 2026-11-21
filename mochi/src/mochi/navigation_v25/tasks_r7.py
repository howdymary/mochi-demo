"""R7 task-only transit caps and a verified final supported stance.

The R5 foot correction is unchanged. R6 smoothing was not promoted. All
success limits, native gait weights and physical-base dynamics stay fixed.
"""
from . import tasks as r2
from .tasks_r5 import TaskWorld
from .task_approaches_r7 import transit as slower_transit
from mochi.balanced.onnx_walk import HoldWalker
from mochi.balanced.sequence import PhysicalStop

_original_finish=r2.finish

def transit(w,goal,task,*args,**kwargs):
    w.station_lift_r5=task in ['drawer','laptop']
    try:return slower_transit(w,goal,task,*args,**kwargs)
    finally:w.station_lift_r5=False

def finish(w,layout,seed,arrivals,failure,started,until):
    if until=='all' and failure is None:
        w.phase='final-supported-settle';w.efficiency_segment='final_settle'
        w.walker=HoldWalker(w,neutral=True)
        end=float(w.d.time)+3.;stable=0.;begin=float(w.d.time)
        try:
            while w.d.time<end:
                w.step()
                good=all(w.foot_touching(s) for s in ['left','right'])
                stable=stable+w.m.opt.timestep if good else 0.
                if stable>=.4:break
            if stable<.4:failure='final-supported-stance-timeout'
        except PhysicalStop as error:failure=str(error)
        w.events.append({'t':float(w.d.time),'phase':'final-supported-stance',
            'success':stable>=.4,'dwell_s':stable,'duration_s':float(w.d.time)-begin,
            'feet':{s:w.sole_patch(s) for s in ['left','right']},
            'controller':'Existing torque-limited neutral-stance blend; physical base remains free.'})
    return _original_finish(w,layout,seed,arrivals,failure,started,until)

def run(*args,**kwargs):
    old_world,old_transit,old_finish=r2.TaskWorld,r2.transit,r2.finish
    r2.TaskWorld,r2.transit,r2.finish=TaskWorld,transit,finish
    try:return r2.run(*args,**kwargs)
    finally:r2.TaskWorld,r2.transit,r2.finish=old_world,old_transit,old_finish
