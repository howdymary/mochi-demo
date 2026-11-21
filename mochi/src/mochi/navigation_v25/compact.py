"""A compact, outcome-free representation for a possible follow-up curriculum.

This does not change the physical planner, available actions or verifier.
The parent and trained policies must use the identical representation.
"""
import json
import math

ACTIONS=['direct','buffered']


def state(observed):
    candidates={}
    for name in ACTIONS:
        p=observed['options'][name]
        candidate={'geometric_route_available':bool(p['feasible'])}
        if p['feasible']:
            turns=p['turns_degrees'];clearance=p['minimum_planned_clearance_mm']
            parameters=p['parameters']
            candidate.update(length_mm=p['length_mm'],minimum_clearance_mm=clearance,
                clearance_band='below_5_mm' if clearance<5 else '5_to_15_mm' if clearance<15 else 'at_least_15_mm',
                turn_count=len(turns),total_turn_degrees=round(sum(abs(t) for t in turns),1),
                largest_turn_degrees=round(max([abs(t) for t in turns] or [0]),1),
                speed_m_per_s=parameters['speed'],yaw_rate_rad_per_s=parameters['yaw_rate'],
                linear_time_proxy_s=round(p['length_mm']/1000/parameters['speed'],2),
                turn_time_proxy_s=round(math.radians(sum(abs(t) for t in turns))/parameters['yaw_rate'],2))
        candidates[name]=candidate
    return {'information':'Privileged planner summaries. No experiment results, layout identifiers or split labels.',
        'target_body_mm':observed['target_body_mm'],'target_heading_degrees':observed['target_heading_degrees'],
        'robot_planning_radius_mm':observed['robot_planning_radius_mm'],'candidates':candidates,
        'proxy_limits':'Geometric availability and timing proxies do not establish dynamic support or moving-foot clearance.'}


def decision(observed):
    from tinker_cookbook.recipes.decisions import Decision
    compact=state(observed)
    return Decision('Select one physical navigation profile. Actual stable, collision-free arrival and the 4.5 mm moving-foot-clearance requirement take priority over efficiency. '
        'Among qualified outcomes minimize measured steps, then time. The same fixed native gait executes every choice. '
        'Learn the tradeoff from measured training examples; timing proxies are not rewards.\nState: '+json.dumps(compact,sort_keys=True),
        [(a,a+': '+json.dumps(compact['candidates'][a],sort_keys=True)) for a in ACTIONS])
