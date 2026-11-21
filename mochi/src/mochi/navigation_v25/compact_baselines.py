"""Fixed and conditional two-profile controls fit only to measured training."""
import numpy as np
from .compact import ACTIONS,state

def features(obs):
    s=state(obs);v=[*s['target_body_mm'],s['target_heading_degrees']]
    for name in ACTIONS:
        p=s['candidates'][name]
        v.extend([float(p['geometric_route_available']),p.get('length_mm',3000),p.get('minimum_clearance_mm',0),
            p.get('turn_count',12),p.get('total_turn_degrees',720),p.get('largest_turn_degrees',180)])
    return v

def tune(records):
    reward=lambda r,a:sum(o['reward'] for o in r['outcomes'][a])
    fixed=max(ACTIONS,key=lambda a:sum(reward(r,a) for r in records))
    matrix=np.array([features(r['observations'][0]) for r in records])
    best={'feature':0,'threshold':0.,'left':fixed,'right':fixed,'reward':sum(reward(r,fixed) for r in records)}
    for column in range(matrix.shape[1]):
        values=np.unique(matrix[:,column])
        for threshold in (values[:-1]+values[1:])/2:
            take=matrix[:,column]<=threshold
            left=max(ACTIONS,key=lambda a:sum(reward(r,a) for r,t in zip(records,take) if t))
            right=max(ACTIONS,key=lambda a:sum(reward(r,a) for r,t in zip(records,take) if not t))
            score=sum(reward(r,left if t else right) for r,t in zip(records,take))
            if score>best['reward']:best={'feature':column,'threshold':float(threshold),'left':left,'right':right,'reward':score}
    return {'fixed':fixed,'contextual':best,'scope':'Same measured training data and two-profile action space as the compact learned policy.'}

def contextual(obs,fit):
    return fit['left'] if features(obs)[fit['feature']]<=fit['threshold'] else fit['right']
