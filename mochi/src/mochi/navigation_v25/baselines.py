"""Training-only fixed selection and a contextual decision-stump control."""
import numpy as np
from .engine import ACTIONS


def features(obs):
    v=[*obs['target_body_mm'],obs['target_heading_degrees']]
    for a in ACTIONS:
        p=obs['options'][a]
        turns=p.get('turns_degrees',[])
        v.extend([float(p['feasible']),p.get('length_mm',3000),p.get('minimum_planned_clearance_mm',0),
            len(turns),sum(abs(t) for t in turns),max([abs(t) for t in turns]or[0])])
    return v


def tune(records):
    # The fixed and contextual controls see every collected interaction,
    # including layouts for which no profile qualified across both seeds.
    valid=list(records)
    def reward(r,a):
        return sum(o['reward'] for o in r['outcomes'][a])
    fixed=max(ACTIONS,key=lambda a:sum(reward(r,a) for r in valid))
    matrix=np.array([features(r['observations'][0]) for r in valid])
    best={'feature':0,'threshold':0.,'left':fixed,'right':fixed,'reward':sum(reward(r,fixed) for r in valid)}
    for column in range(matrix.shape[1]):
        unique=np.unique(matrix[:,column])
        for threshold in (unique[:-1]+unique[1:])/2:
            take=matrix[:,column]<=threshold
            left=max(ACTIONS,key=lambda a:sum(reward(r,a) for r,t in zip(valid,take) if t))
            right=max(ACTIONS,key=lambda a:sum(reward(r,a) for r,t in zip(valid,take) if not t))
            value=sum(reward(r,left if t else right) for r,t in zip(valid,take))
            if value>best['reward']:
                best={'feature':column,'threshold':float(threshold),'left':left,'right':right,'reward':value}
    return {'fixed':fixed,'contextual':best,'scope':'Uses exactly the same measured training interactions as the learned model.'}


def contextual(obs,fit):
    return fit['left'] if features(obs)[fit['feature']]<=fit['threshold'] else fit['right']


def comparison(reference,candidate):
    from collections import defaultdict
    a={(r['layout_sha256'],r['seed']):r for r in reference};b={(r['layout_sha256'],r['seed']):r for r in candidate}
    assert a.keys()==b.keys()
    groups=defaultdict(list)
    for key in a:
        x,y=a[key],b[key]
        assert x['initial_physical_state_sha256']==y['initial_physical_state_sha256'] and x['mechanics_sha256']==y['mechanics_sha256']
        groups[key[0]].append((x,y))
    step_layout=[];time_layout=[]
    for values in groups.values():
        both=[(x,y) for x,y in values if x['qualified'] and y['qualified']]
        if both:
            step_layout.append(np.mean([y['steps']['attempts'] for x,y in both])/np.mean([x['steps']['attempts'] for x,y in both]))
            time_layout.append(np.mean([y['physical_seconds'] for x,y in both])/np.mean([x['physical_seconds'] for x,y in both]))
    no_new_failures=all(not x['qualified'] or b[k]['qualified'] for k,x in a.items())
    ratio=float(np.mean(step_layout)) if step_layout else None
    time_ratio=float(np.mean(time_layout)) if time_layout else None
    improved=sum(v<1 for v in step_layout)
    rng=np.random.default_rng(251709)
    if step_layout:
        indices=rng.integers(0,len(step_layout),size=(10000,len(step_layout)))
        interval=np.quantile(np.asarray(step_layout)[indices].mean(axis=1),[.025,.975]).tolist()
    else:
        interval=None
    return {'layouts':len(groups),'reference_qualified':sum(r['qualified'] for r in reference),
        'candidate_qualified':sum(r['qualified'] for r in candidate),'newly_failed_reference_successes':not no_new_failures,
        'mean_layout_step_ratio':ratio,'mean_layout_time_ratio':time_ratio,'improved_layouts':improved,
        'step_ratio_layout_bootstrap_95_percent_interval':interval,
        'uncertainty_scope':'Paired layout bootstrap, 10,000 resamples; seeds within a layout are not independent layouts. Descriptive interval for the jointly qualified subset.',
        'win':bool(no_new_failures and ratio is not None and ratio<=.95 and time_ratio<=1.05 and improved>=4
            and not any(r['fall'] or r['invalid_contact'] for r in candidate)),
        'scope':'Matched source, layouts and physical resets. Efficiency uses only jointly qualified attempts, averaged within layout.'}
