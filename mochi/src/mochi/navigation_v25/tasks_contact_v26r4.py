"""R4 reserves translation tracking room on the oriented corridor fallback."""
from . import tasks as original
from .tasks_contact_v26r3 import TaskWorld,transit,finish,policy
from .heading_approach_r4_v26 import candidate_approach

def run(*args,**kwargs):
    previous=original.TaskWorld,original.transit,original.finish,original.policy,original.candidate_approach
    original.TaskWorld,original.transit,original.finish,original.policy,original.candidate_approach=TaskWorld,transit,finish,policy,candidate_approach
    try:return original.run(*args,**kwargs)
    finally:original.TaskWorld,original.transit,original.finish,original.policy,original.candidate_approach=previous
