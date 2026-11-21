"""Measured-velocity contact control with a nominal gravity/friction model.

The controller uses current hinge angle, speed and foot loads. It does not
read the randomized mass/friction or outcomes. All forces remain actuator
commands under the original global contact-force and success verifiers.
"""
import math
from dataclasses import asdict
import mujoco
import numpy as np
from mochi.curriculum.world import DT
from mochi.control_v8.manipulation import approach_points as canonical_approach_points, lid_target as canonical_lid_target
from mochi.control_v8.verification import laptop_good,task_valid

def laptop_surface(world,angle,radius,x,depth):
 point,normal=canonical_lid_target(angle,radius,x,depth)
 hinge=world.d.xpos[world.id('body','laptop-screen')]
 return point+hinge-np.array([.14,.249,.0185]),normal

def adaptive_laptop(self,p,horizon):
 # Only fixture translation is varied in this study. Keep the contact law,
 # force guards and success predicates, expressing its targets at the actual hinge.
 hinge=self.d.xpos[self.id('body','laptop-screen')].copy()
 offset=hinge-np.array([.14,.249,.0185])
 def lid_target(angle,radius,x,depth):
  return laptop_surface(self,angle,radius,x,depth)
 def approach_points(world,profile,angle):
  points,normal=canonical_approach_points(world,profile,angle)
  return [points[0],points[1]+offset],normal
 def contact_geometry():
  rows=[];gid=self.object_geoms['laptop'];lid=self.id('body','laptop-screen');span=self.d.xmat[lid].reshape(3,3)[:,2]
  for i,c in enumerate(self.d.contact):
   if gid not in [int(c.geom1),int(c.geom2)]:continue
   other=int(c.geom2) if int(c.geom1)==gid else int(c.geom1)
   if other not in self.hand_geoms['left']:continue
   f=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,f)
   rows.append({'hand_geom':mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,other),'position':c.pos.tolist(),
    'normal':c.frame[:3].tolist(),'lid_to_hand_normal':(c.frame[:3] if int(c.geom1)==gid else -c.frame[:3]).tolist(),'hand_center':self.d.geom_xpos[other].tolist(),'tip_position':self.d.site_xpos[self.arm['left']['tip']].tolist(),'normal_force_n':float(f[0]),
    'cap_normal_alignment':float(abs(c.frame[:3]@span)),
    'contact_radial_m':float((c.pos-self.d.xpos[lid])@span)})
  return rows
 self.task='laptop';self.approach_side='left';self.approach_path=[];self.phase='approach';self.t0=float(self.d.time);self.hand_contacts=0;self.max_force=0.;self.bad_contacts=0;self.progress_contact=0.;first_angle=None;arm=self.arm['left'];qtarget=self.d.qpos[arm['qs']].copy();next_control=-1.;next_ik=-1.;dwell=0.;push_start=None;release_point=None;release_normal=None;abort=None;approach_stage=0;posture=None;force_integral=0.;force_log=[];next_force_log=-1.;stall_angle=None;stall_time=None;pulse_finish=False;reapproaches=0;last_contact_t=float(self.d.time)
 while self.d.time-self.t0<horizon and not self.fall:
  elapsed=float(self.d.time)-self.t0;contact,force,bad=self.contacts('laptop');self.hand_contacts+=int(contact);self.max_force=max(self.max_force,force);self.bad_contacts+=int(bad);a=self.value('laptop')
  if contact and first_angle is None:first_angle=a
  self.progress_contact=0. if first_angle is None else max(0.,first_angle-a)
  if contact:last_contact_t=float(self.d.time)
  lost=(not contact and push_start is not None and float(self.d.time)-last_contact_t>.25 and float(self.d.time)-push_start>.5)
  stuck=(contact and stall_time is not None and float(self.d.time)-stall_time>1.2 and a>math.radians(68))
  if getattr(self,'laptop_reapproach_enabled',False) and self.phase=='push' and reapproaches<3 and (lost or stuck):
   self.phase='approach';approach_stage=1;next_ik=-1.;next_control=-1.;force_integral=0.;stall_angle=None;stall_time=None;pulse_finish=False;reapproaches+=1
   self.events.append({'t':float(self.d.time),'phase':'laptop-reapproach','attempt':reapproaches,'reason':'lost_contact' if lost else 'stalled_contact'})
  if self.phase=='approach':
   waypoints,normal=approach_points(self,p,a);target=waypoints[min(approach_stage,1)]
   if np.linalg.norm(self.d.site_xpos[arm['tip']]-target)<(.006 if reapproaches else .010):
    if approach_stage<1:approach_stage+=1
    else:self.phase='push';push_start=float(self.d.time);posture=self.d.qpos[arm['qs']].copy()
  if self.phase=='push' and a<math.radians(p.release_degrees):
   self.phase='release';release_point=self.d.site_xpos[arm['tip']].copy();_,release_normal=lid_target(a,p.radius,p.contact_x,0)
  if self.d.time>=next_control:
   if self.phase=='push':target,normal=lid_target(a,p.radius,p.contact_x,0.)
   elif self.phase=='release':target=release_point+release_normal*.018;normal=release_normal
   else:
    waypoints,normal=approach_points(self,p,a);target=waypoints[min(approach_stage,1)]
   if self.phase!='push':
    if self.d.time>=next_ik:qtarget=self.ik('left',target,normal,from_home=True);next_ik=float(self.d.time)+.06
    change=qtarget-self.d.ctrl[arm['acts']];change*=min(1.,p.slew/max(float(np.max(np.abs(change))),1e-8));self.d.ctrl[arm['acts']]=np.clip(self.d.ctrl[arm['acts']]+change,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
   elif not contact:
    seek,normal=lid_target(a,p.radius,p.contact_x,-.0003);delta=seek-self.d.site_xpos[arm['tip']];delta*=min(1.,.0004/max(float(np.linalg.norm(delta)),1e-9));J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);J=J[:,arm['vs']];dq=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,delta);self.d.ctrl[arm['acts']]=np.clip(self.d.qpos[arm['qs']]+dq,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
   next_control=float(self.d.time)+.02
  if self.phase=='push' and contact:
   surface,normal=lid_target(a,p.radius,p.contact_x,0.);J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);velocity=J@self.d.qvel
   tangent=np.eye(3)-np.outer(normal,normal)
   if getattr(self,'laptop_hinge_projection',False):
    object_jac=np.zeros((3,self.m.nv));mujoco.mj_jac(self.m,self.d,object_jac,None,surface,self.id('body','laptop-screen'))
    direction=object_jac[:,self.v['laptop']];direction/=max(float(np.linalg.norm(direction)),1e-9)
    tangent=np.eye(3)-np.outer(direction,direction)
   error=tangent@(surface-self.d.site_xpos[arm['tip']]);active=(float(self.d.time)-push_start)%(p.pulse_on+p.pulse_off)<p.pulse_on;ramp=min(1.,(float(self.d.time)-push_start)/.3);press=p.force*ramp if active else .04;feet=np.mean([self.d.xpos[self.id('body',s+'_ankle_roll_link')] for s in ['left','right']],axis=0);horizontal=float(np.clip((surface[1]-feet[1])/max(surface[2],.06),-.1,.4));lever=max(.035,p.radius*(math.cos(a)+horizontal*math.sin(a)));closing_speed=float(self.d.qvel[self.v['laptop']]);desired_speed=getattr(self,'contact_closing_speed',.16);force_integral=float(np.clip(force_integral+(desired_speed-closing_speed)*DT,-.2,.3));gravity=.16*9.81*.075*math.cos(a);feedforward=(.070+.065*desired_speed-gravity)/lever;press=float(np.clip(feedforward+.6*(desired_speed-closing_speed)+.3*force_integral,.025,p.force))*ramp;loads=self.loads();minimum_load=min(loads.values());support_scale=float(np.clip((minimum_load-.06)/.18,0.,1.));press=min(press,.04+support_scale*p.force)
   if stall_angle is None or stall_angle-a>.02:stall_angle=a;stall_time=float(self.d.time)
   if a<math.radians(getattr(self,'laptop_pulse_degrees',68)) and float(self.d.time)-stall_time>getattr(self,'laptop_pulse_delay_s',1.2):pulse_finish=True
   if pulse_finish:
    phase_time=(float(self.d.time)-push_start)%.45
    press=min(getattr(self,'laptop_pulse_force_n',.60),p.force) if phase_time<.30 else .04
    ramp_s=getattr(self,'laptop_pulse_ramp_s',0.)
    if ramp_s>0 and phase_time<.30:
     blend=min(phase_time/ramp_s,1.,(.30-phase_time)/ramp_s);blend=blend*blend*(3.-2.*blend)
     press=.04+(press-.04)*blend
   F=np.array([0.,-horizontal,-1.])*press+8*error-.5*(tangent@velocity if getattr(self,'laptop_project_damping',False) else velocity);Ja=J[:,arm['vs']];inverse=Ja.T@np.linalg.inv(Ja@Ja.T+np.eye(3)*8e-8);N=np.eye(7)-inverse@Ja;tau=Ja.T@F+N.T@(.15*(posture-self.d.qpos[arm['qs']])-.01*self.d.qvel[arm['vs']]);kp=self.m.actuator_gainprm[arm['acts'],0];kv=-self.m.actuator_biasprm[arm['acts'],2];self.d.ctrl[arm['acts']]=np.clip(self.d.qpos[arm['qs']]+(tau+kv*self.d.qvel[arm['vs']])/kp,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
  # Actuator feedback at the physics rate; never clamps contact forces or
  # changes object state. It releases elastic preload when measured force rises.
  if force>getattr(self,"laptop_force_backoff_n",.65):
   _,outward=lid_target(a,p.radius,p.contact_x,0);J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);J=J[:,arm['vs']];dq=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,outward*.00015);self.d.ctrl[arm['acts']]=np.clip(self.d.qpos[arm['qs']]+dq,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
  if self.d.time>=next_force_log:
   force_log.append({'t':float(self.d.time),'angle':a,'closing_speed_rad_s':float(self.d.qvel[self.v['laptop']]),'loads_n':self.loads(),'phase':self.phase,'mode':'pulse_finish' if pulse_finish else 'velocity_feedback','contact_geometry':contact_geometry()});next_force_log=float(self.d.time)+.05
  self.step(standing=True)
  speed=float(self.d.qvel[self.v['laptop']]);good=laptop_good(self.value('laptop'),speed,self.progress_contact);dwell=dwell+DT if self.phase=='release' and good else 0.
  if dwell>.35:break
  if self.max_force>.8:abort='force_limit';break
 result={'task':'laptop','success':task_valid(dwell,self.hand_contacts,self.bad_contacts,self.fall,self.max_force),'value':self.value('laptop'),'duration':float(self.d.time)-self.t0,'contacts':self.hand_contacts,'non_hand_contact_steps':self.bad_contacts,'max_force_n':self.max_force,'fall':self.fall,'max_tilt_deg':math.degrees(self.max_tilt),'profile':asdict(p),'phase':self.phase,'contact_progress':self.progress_contact,'abort':abort,'approach_stage':approach_stage,'final_tip':self.d.site_xpos[arm['tip']].tolist(),'final_target':target.tolist()};result['controller']='Profile-specific measured-force backoff; original joint actuators, support guard, 0.8 N global verifier and object-success checks unchanged';result['force_schedule_log']=force_log;result['reapproaches']=reapproaches;self.results['laptop']=result;self.events.append({**result,'t':float(self.d.time)});return result
