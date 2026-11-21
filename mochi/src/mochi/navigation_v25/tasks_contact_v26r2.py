"""Scope the station-transit refinement to desk-level task approaches."""
from . import tasks as original
from .tasks_contact_v26 import TaskWorld, policy
from .tasks import transit as terrain_transit
from .task_approaches_r9 import transit as station_transit
from .tasks_r7 import finish

def transit(w, goal, task, *args, **kwargs):
    controller = station_transit if task in ['drawer', 'laptop', 'globe'] else terrain_transit
    return controller(w, goal, task, *args, **kwargs)

def run(*args, **kwargs):
    previous = original.TaskWorld, original.transit, original.finish, original.policy
    original.TaskWorld, original.transit, original.finish, original.policy = TaskWorld, transit, finish, policy
    try:
        return original.run(*args, **kwargs)
    finally:
        original.TaskWorld, original.transit, original.finish, original.policy = previous
