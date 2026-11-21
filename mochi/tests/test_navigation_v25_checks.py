"""Guard against overstated efficiency and weakened controls."""
import copy
import json
import unittest

from mochi.navigation_v25.baselines import comparison, tune


def outcome(layout,seed,steps,qualified=True):
    return dict(layout_sha256=layout,seed=seed,steps={'attempts':steps},qualified=qualified,
        physical_seconds=steps/8,initial_physical_state_sha256=layout+str(seed),
        mechanics_sha256='unchanged',fall=False,invalid_contact=False)


class ComparisonChecks(unittest.TestCase):
    def test_comparison_can_be_persisted_as_json(self):
        report=comparison([outcome('a',0,100)],[outcome('a',0,80)])
        self.assertEqual(json.loads(json.dumps(report))['improved_layouts'],1)

    def test_a_short_failed_attempt_is_not_an_efficiency_gain(self):
        a=[outcome('a',0,100),outcome('b',0,100)]
        b=[outcome('a',0,50),outcome('b',0,1,False)]
        r=comparison(a,b)
        self.assertEqual(r['mean_layout_step_ratio'],.5)
        self.assertTrue(r['newly_failed_reference_successes'])
        self.assertFalse(r['win'])

    def test_seeds_do_not_become_independent_layouts(self):
        a=[outcome('a',i,100) for i in range(3)]+[outcome('b',0,100)]
        b=[outcome('a',i,50) for i in range(3)]+[outcome('b',0,100)]
        self.assertEqual(comparison(a,list(reversed(b)))['mean_layout_step_ratio'],.75)

    def test_changed_initial_physics_cannot_be_called_a_checkpoint_comparison(self):
        a=[outcome('a',0,100)];b=copy.deepcopy(a)
        b[0]['initial_physical_state_sha256']='different'
        with self.assertRaises(AssertionError):comparison(a,b)

    def test_fixed_control_sees_cases_without_a_robust_teacher_label(self):
        obs={'target_body_mm':[0,0],'target_heading_degrees':0,
            'options':{a:{'feasible':True} for a in ['direct','buffered','wide_fast']}}
        records=[{'target':'direct','observations':[obs],
            'outcomes':{a:[{'reward':r}] for a,r in [('direct',900),('buffered',850),('wide_fast',800)]}},
            {'target':None,'observations':[obs],
            'outcomes':{a:[{'reward':r}] for a,r in [('direct',-1000000),('buffered',800),('wide_fast',-1000000)]}}]
        self.assertEqual(tune(records)['fixed'],'buffered')


if __name__=='__main__':unittest.main()
