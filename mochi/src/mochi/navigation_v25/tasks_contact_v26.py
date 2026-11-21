"""Development-selected contact engineering, shared by both frozen models."""
from . import tasks as original
from .tasks import TaskWorld as OriginalWorld
from .task_approaches_r9 import transit
from .tasks_r7 import finish
from . import policy_contact_v26 as policy
from .laptop_contact_v26 import adaptive_laptop

class TaskWorld(OriginalWorld):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        overrides = self.layout.get('physics_overrides', {})
        if 'laptop_friction' in overrides:
            value = float(overrides['laptop_friction'])
            assert .05 <= value <= .08
            self.m.dof_frictionloss[self.v['laptop']] = value
            self.s['laptop_friction'] = value

    def laptop(self, profile, horizon):
        return adaptive_laptop(self, profile, horizon)

def run(*args, **kwargs):
    previous = original.TaskWorld, original.transit, original.finish, original.policy
    original.TaskWorld, original.transit, original.finish, original.policy = TaskWorld, transit, finish, policy
    try:
        return original.run(*args, **kwargs)
    finally:
        original.TaskWorld, original.transit, original.finish, original.policy = previous
