"""Explain recorded gate failures. Never changes qualification or control."""
def quality_misses(row,cfg):
    if row['qualified_complete']:return []
    e=row['episode'];limits=cfg['smoothness'];misses=[]
    if not row['complete_sequence_success']:misses.append(row['failure'] or 'complete sequence or final support check failed')
    if not e['efficiency_validity']:misses.append('support or movement validity check failed')
    checks=[(e['balance_metrics']['roll_rms_deg'],limits['roll_rms_degrees_max'],'body roll RMS','degrees'),
        (e['balance_metrics']['roll_peak_deg'],limits['roll_peak_degrees_max'],'peak body roll','degrees'),
        (e['balance_metrics']['lateral_rms_m'],limits['path_lateral_rms_m_max'],'lateral path RMS','m'),
        (e['balance_metrics']['lateral_peak_to_peak_m'],limits['path_lateral_peak_to_peak_m_max'],'lateral path range','m'),
        (e['duration'],limits['sequence_time_seconds_max'],'sequence duration','s'),
        (sum(e['foot_slip_estimate_m'].values()),limits['loaded_contact_travel_estimate_m_max'],'loaded contact travel estimate','m'),
        (e['native_smoothness']['sampled_acceleration_rms_rad_s2'],limits['native_acceleration_rms_max'],'native joint acceleration RMS','rad/s²'),
        (e['native_smoothness']['sampled_torque_change_rms_nm'],limits['native_torque_change_rms_max'],'native torque-change RMS','Nm')]
    for value,limit,label,unit in checks:
        if value is None or value>limit:misses.append(f'{label} {value} {unit} exceeds {limit}')
    forward=row['direction_metrics']['forward_facing_fraction']
    if forward is None:misses.append('forward-facing travel measurement missing')
    elif forward<.9:misses.append(f'forward-facing travel {forward*100:.1f}% below 90%')
    legs=e.get('flat_legs',[])
    if len(legs)!=3:misses.append(f'only {len(legs)}/3 walking legs completed')
    for leg in legs:
        if not leg['success'] or leg['moving_swings']<2:misses.append(leg['task']+' walking verification failed')
        elif leg['moving_minimum_sole_clearance_m'] is None:misses.append(leg['task']+' foot-clearance measurement missing')
        elif leg['moving_minimum_sole_clearance_m']<.0045:
            misses.append(f"{leg['task']} sole clearance {leg['moving_minimum_sole_clearance_m']*1000:.3f} mm below 4.5 mm")
    if e.get('paper_geometry_present'):misses.append('removed paper obstacle present')
    return misses
