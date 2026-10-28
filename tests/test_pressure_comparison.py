"""Pressure summaries retain paired observations and equal event weights."""
import pytest
from borethm.studies.pressure_comparison import summaries


def record(event,prediction,target=200.,status='ok'):
    return dict(well='test',role='primary',bha='2',variant='model',scenario='case',
                event_id=event,status=status,solver_success=status=='ok',
                comparison_target_psi=target,predicted_low_psi=prediction,
                predicted_high_psi=prediction,flow_gpm=500.,bit_depth_ft=1000.)


def test_long_event_cannot_outweigh_short_event():
    rows=[record('long',100.) for _ in range(9)]+[record('short',300.)]
    events,bhas=summaries(rows)
    assert len(events)==2
    assert bhas[0]['planned_windows']==10
    assert bhas[0]['compared_events']==2
    assert bhas[0]['residual_low_psi_median']==0.
    assert bhas[0]['residual_low_psi_min']==-100.
    assert bhas[0]['residual_low_psi_max']==100.


def test_failed_and_missing_windows_cannot_enter_the_paired_medians():
    rows=[record('event',250.),record('event',900.,status='solver_failure'),
          record('event',1000.,status='missing_target')]
    events,bhas=summaries(rows)
    assert events[0]['compared']==1
    assert events[0]['comparison_target_psi']==200.
    assert events[0]['residual_low_psi']==50.
    assert bhas[0]['failed_windows']==bhas[0]['missing_target_windows']==1


def test_motor_interval_uses_median_endpoints_and_retains_zero_denominator():
    a=record('event',10.,target=0.);a.update(is_motor_interval=True,predicted_high_psi=30.)
    b=record('event',-20.,target=0.);b.update(is_motor_interval=True,predicted_high_psi=20.)
    events,bhas=summaries([a,b])
    assert events[0]['predicted_low_psi']==-5.
    assert events[0]['predicted_high_psi']==25.
    assert events[0]['interval_coverage']
    assert events[0]['residual_low_percent'] is None
    assert bhas[0]['interval_coverage_fraction']==1.


@pytest.mark.parametrize('eow,trial_run', [('17','BHA10'),('18','BHA11'),('19','BHA12'),('20','BHA13')])
def test_trial_adapter_preserves_aggregate_thermal_geometry(eow,trial_run):
    from borethm.studies import validate_forge16b as trial
    from borethm.studies.pressure_comparison import serial_development_geometry
    depth=sum(trial.DEPTHS[trial_run])/2
    original=trial.geometry(trial_run,depth,4.9237482416889895)
    revised=serial_development_geometry(dict(well='16B',run=eow),{},original,'EIS')
    assert len(revised.string)==len(original.string)
    assert revised.hole==original.hole and revised.survey is original.survey
    for before,after in zip(original.string,revised.string):
        assert after.length==before.length
        assert after.pipe.layers==before.pipe.layers
        assert after.pipe.name==before.pipe.name
        if before.pipe.name==trial.HWDP.name:
            assert after.pipe.hydraulic_joint.bore_diameter==2*before.pipe.r_bore
            assert after.pipe.hydraulic_joint.spacing==trial.HWDP_JOINT_FT*trial.FT
        elif before.pipe.name==trial.DRILL_PIPE.name or before.pipe.name.startswith('IDP,'):
            assert after.pipe.hydraulic_joint.spacing==(2378/75)*trial.FT
        else:
            assert after.pipe.hydraulic_joint is None
