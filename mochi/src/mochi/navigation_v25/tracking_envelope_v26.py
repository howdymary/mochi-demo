"""Sampled translation uncertainty for planning copies, never live state changes."""
import math
from .task_approaches import pose_corridor_clear

def tracking_corridor_clear(w,start,goal,turn_at_goal=True,radius=.016):
    if not pose_corridor_clear(w,start,goal,turn_at_goal):return False
    diagonal=radius/math.sqrt(2)
    offsets=[(-radius,0.),(radius,0.),(0.,-radius),(0.,radius),
        (-diagonal,-diagonal),(-diagonal,diagonal),(diagonal,-diagonal),(diagonal,diagonal)]
    for dx,dy in offsets:
        a=[start[0]+dx,start[1]+dy,start[2]];b=[goal[0]+dx,goal[1]+dy,goal[2]]
        if not pose_corridor_clear(w,a,b,turn_at_goal):return False
    return True
