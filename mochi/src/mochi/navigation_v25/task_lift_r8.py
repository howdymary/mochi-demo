"""Task-only actuator filtering around a fixed native gait and R5 sole feedback."""
import math
import numpy as np
from .task_lift_r5 import StationSoleFeedbackWalker

class FilteredStationWalker(StationSoleFeedbackWalker):
    def command(self,velocity):
        before=self.d.ctrl[self.aids].copy()
        super().command(velocity)
        if not hasattr(self,'torque_filter_state'):
            self.torque_filter_state=before
            self.torque_filter_time=float(self.d.time)-self.m.opt.timestep
        dt=max(0.,min(.01,float(self.d.time)-self.torque_filter_time));self.torque_filter_time=float(self.d.time)
        tau=getattr(self.w,'station_torque_filter_tau_s',.004)
        assert .001<=tau<=.008
        self.torque_filter_state+=(1.-math.exp(-dt/tau))*(self.d.ctrl[self.aids]-self.torque_filter_state)
        limits=self.m.actuator_forcerange[self.aids]
        self.d.ctrl[self.aids]=np.clip(self.torque_filter_state,limits[:,0],limits[:,1])

    def description(self):
        return {**super().description(),'leg_actuator_torque_filter':{
            'time_constant_s':getattr(self.w,'station_torque_filter_tau_s',.004),
            'native_weights_trained':False,'unchanged_actuator_force_limits':True}}
