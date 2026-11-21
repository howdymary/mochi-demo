"""Explicit revised laptop options; no model-weight or verifier changes."""
from dataclasses import replace
from mochi.navigation_tasks_v24 import policy as original
from mochi.contact_v18.policy import PRESSES

def observation(w, domain, task):
    value = original.observation(w, domain, task)
    value['control_revision'] = 'contact-v26'
    return value

def decision(obs):
    item = original.decision(obs)
    if obs['domain'] != 'laptop':
        return item
    from tinker_cookbook.recipes.decisions import Decision
    return Decision(item.text, [
        ('P5', 'Object-relative upper-edge contact; adaptive closing speed 0.40 rad/s, commanded force cap 0.72 N, measured-force backoff at 0.74 N, 64 second horizon. Stalled closure below 78 degrees uses bounded 0.30/0.15 second pulse recovery. Global 0.8 N force verifier unchanged.'),
        ('L0', 'Same object-relative adaptive controller with closing speed 0.30 rad/s, commanded force cap 0.55 N, measured-force backoff at 0.65 N, and 64 second horizon. Same global safety and success verifiers.')])

def execute(w, domain, task, action):
    if domain != 'laptop':
        return original.execute(w, domain, task, action)
    assert action in original.ACTIONS[domain]
    p = replace(PRESSES['P5'], force=.72 if action == 'P5' else .55)
    w.contact_closing_speed = .4 if action == 'P5' else .3
    w.laptop_force_backoff_n = .74 if action == 'P5' else .65
    w.laptop_pulse_force_n = .72 if action == 'P5' else .55
    w.laptop_pulse_degrees = 78.
    w.laptop_pulse_delay_s = .4
    w.efficiency_segment = 'manipulation'
    return w.do_task('laptop', p, max_seconds=64.)
