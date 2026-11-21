import copy
import json
import unittest
from mochi.navigation_v25.compact import state,ACTIONS

def observed():
    return {'target_body_mm':[100,20],'target_heading_degrees':90,'robot_planning_radius_mm':75,
        'options':{a:{'feasible':True,'parameters':{'speed':.1,'yaw_rate':.75},'length_mm':200,
            'minimum_planned_clearance_mm':4.3,'turns_degrees':[90,-30]} for a in ['direct','buffered','wide_fast']}}

class CompactContract(unittest.TestCase):
    def test_training_labels_and_split_identifiers_do_not_enter_model_state(self):
        a=observed();b=copy.deepcopy(a)
        b.update(layout_id='SECRET_LAYOUT',seed=999,partition='FINAL_SPLIT',target='TEACHER_ACTION',outcomes={'reward':1e9})
        self.assertEqual(state(a),state(b))
        encoded=json.dumps(state(b))
        for value in ['SECRET_LAYOUT','FINAL_SPLIT','TEACHER_ACTION','1000000000']:self.assertNotIn(value,encoded)

    def test_only_declared_actions_and_geometric_information_are_exposed(self):
        result=state(observed())
        self.assertEqual(set(result['candidates']),set(ACTIONS))
        self.assertNotIn('wide_fast',result['candidates'])
        self.assertEqual(result['candidates']['direct']['linear_time_proxy_s'],2)

    def test_an_unavailable_path_does_not_get_invented_success_or_timing(self):
        a=observed();a['options']['direct']={'feasible':False}
        self.assertEqual(state(a)['candidates']['direct'],{'geometric_route_available':False})

if __name__=='__main__':unittest.main()
