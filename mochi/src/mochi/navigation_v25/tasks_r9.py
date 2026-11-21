"""R9 development candidate: later final heading and a modest native swing lift."""
from . import tasks as r2
from .tasks import TaskWorld
from .task_approaches_r9 import transit
from .tasks_r7 import finish

def run(*args,**kwargs):
    old_world,old_transit,old_finish=r2.TaskWorld,r2.transit,r2.finish
    r2.TaskWorld,r2.transit,r2.finish=TaskWorld,transit,finish
    try:return r2.run(*args,**kwargs)
    finally:r2.TaskWorld,r2.transit,r2.finish=old_world,old_transit,old_finish
