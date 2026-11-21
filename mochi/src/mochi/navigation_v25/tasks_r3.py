"""Task-only engineering revision: measured sole feedback on station transits.

The R2 task implementation and navigation study remain frozen. This wrapper is
used in a dedicated physical process, never concurrently with another revision.
Both checkpoint sides must use this same controller revision.
"""
from . import tasks as r2
from .task_approaches import transit as r2_transit
from .task_lift import SoleFeedbackWalker
from mochi.balanced.onnx_walk import HubWalker


class TaskWorld(r2.TaskWorld):
    def step(self, *args, **kwargs):
        if (getattr(self, 'station_sole_feedback', False)
                and isinstance(self.walker, HubWalker)
                and not isinstance(self.walker, SoleFeedbackWalker)):
            self.walker.__class__ = SoleFeedbackWalker
        return super().step(*args, **kwargs)


def transit(w, goal, task, *args, **kwargs):
    w.station_sole_feedback = task in ['drawer', 'laptop', 'globe']
    try:
        return r2_transit(w, goal, task, *args, **kwargs)
    finally:
        w.station_sole_feedback = False


def run(*args, **kwargs):
    old_world, old_transit = r2.TaskWorld, r2.transit
    r2.TaskWorld, r2.transit = TaskWorld, transit
    try:
        return r2.run(*args, **kwargs)
    finally:
        r2.TaskWorld, r2.transit = old_world, old_transit
