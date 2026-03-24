"""
Test suite for the drone altitude-hold simulation task.
Tests only what is explicitly mentioned in instruction.md.
"""

import importlib.util
import sys

sys.path.insert(0, '/root')


class TestInputFilesIntegrity:
    """Instruction: telemetry.csv has 241 rows; flight_params.yaml defines mission constraints."""

    def test_input_files_integrity(self):
        import pandas as pd
        import yaml

        telemetry = pd.read_csv('/root/telemetry.csv')
        assert len(telemetry) == 241
        assert list(telemetry.columns) == ['time', 'target_altitude', 'wind_accel', 'phase']
        assert telemetry['time'].min() == 0.0
        assert telemetry['time'].max() == 48.0

        with open('/root/flight_params.yaml', 'r', encoding='utf-8') as handle:
            config = yaml.safe_load(handle)

        assert config['drone']['mass_kg'] == 1.8
        assert config['drone']['thrust']['hover_newton'] == 17.7
        assert config['mission']['dt'] == 0.2
        assert config['mission']['safety']['max_accel_mps2'] == 4.0
        assert config['initial_state']['altitude_m'] == 1.5


class TestPIDController:
    """Step 1: PIDController class with __init__, reset, compute methods."""

    def test_pid_controller(self):
        spec = importlib.util.spec_from_file_location('altitude_controller', '/root/altitude_controller.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, 'PIDController')

        controller = module.PIDController(kp=1.0, ki=0.1, kd=0.05)
        assert hasattr(controller, 'reset')
        assert hasattr(controller, 'compute')

        controller.reset()
        out1 = controller.compute(error=1.0, dt=0.2)
        out2 = controller.compute(error=1.0, dt=0.2)
        assert isinstance(out1, (int, float))
        assert out2 > out1


class TestAltitudeHoldSystem:
    """Step 2: AltitudeHoldController class that reads nested config and returns thrust/error."""

    def test_altitude_hold(self):
        import yaml

        spec = importlib.util.spec_from_file_location('altitude_hold', '/root/altitude_hold.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with open('/root/flight_params.yaml', 'r', encoding='utf-8') as handle:
            config = yaml.safe_load(handle)

        assert hasattr(module, 'AltitudeHoldController')

        controller = module.AltitudeHoldController(config)
        thrust_cmd, altitude_error = controller.compute(
            target_altitude=12.0,
            altitude=1.5,
            vertical_speed=0.0,
            dt=0.2,
        )
        assert isinstance(thrust_cmd, (int, float))
        assert isinstance(altitude_error, (int, float))
        assert thrust_cmd > config['drone']['thrust']['hover_newton']


class TestTuningResults:
    """Step 4: altitude_tuning.yaml format and value ranges."""

    def test_tuning_results(self):
        import yaml

        with open('/root/altitude_tuning.yaml', 'r', encoding='utf-8') as handle:
            tuning = yaml.safe_load(handle)

        with open('/root/flight_params.yaml', 'r', encoding='utf-8') as handle:
            config = yaml.safe_load(handle)

        assert set(tuning.keys()) == {'altitude_loop'}
        assert set(tuning['altitude_loop'].keys()) == {'kp', 'ki', 'kd', 'damping_gain'}

        defaults = config['controller']['altitude_hold']['pid']
        assert tuning['altitude_loop']['kp'] != defaults['kp']
        assert tuning['altitude_loop']['ki'] != defaults['ki'] or tuning['altitude_loop']['kd'] != defaults['kd']
        assert tuning['altitude_loop']['damping_gain'] != config['controller']['vertical_damping']['gain']

        assert 0 < tuning['altitude_loop']['kp'] < 6
        assert 0 <= tuning['altitude_loop']['ki'] < 2
        assert 0 <= tuning['altitude_loop']['kd'] < 3
        assert 0 < tuning['altitude_loop']['damping_gain'] <= 2


class TestFlightResults:
    """Step 5: flight_results.csv format, rows, timestamps, and limits."""

    def test_flight_results(self):
        import pandas as pd

        telemetry = pd.read_csv('/root/telemetry.csv')
        results = pd.read_csv('/root/flight_results.csv')

        assert list(results.columns) == [
            'time',
            'target_altitude',
            'altitude',
            'vertical_speed',
            'thrust_cmd',
            'error',
            'phase',
        ]
        assert len(results) == 241
        assert results['time'].tolist() == telemetry['time'].tolist()
        assert set(results['phase'].unique()).issubset({'precheck', 'climb', 'hold', 'descent'})
        assert results['thrust_cmd'].between(0.0, 26.0).all()
        assert results['altitude'].min() >= 0.0


class TestReport:
    """Step 6: altitude_report.md includes design, tuning, and result sections."""

    def test_report_keywords(self):
        with open('/root/altitude_report.md', 'r', encoding='utf-8') as handle:
            content = handle.read().lower()

        assert 'design' in content
        assert 'tuning' in content
        assert 'result' in content


class TestClimbPerformance:
    """Performance targets for the climb segment."""

    def test_climb_performance(self):
        import pandas as pd

        results = pd.read_csv('/root/flight_results.csv')
        climb = results[(results['time'] >= 5.0) & (results['time'] <= 18.0)]

        t10 = climb[climb['altitude'] >= 2.55]['time'].min()
        t90 = climb[climb['altitude'] >= 10.95]['time'].min()
        assert t90 - t10 < 8.0

        overshoot = climb['altitude'].max() - 12.0
        assert overshoot < 0.8


class TestHoldPerformance:
    """Performance target for the gust-hold window."""

    def test_hold_performance(self):
        import pandas as pd

        results = pd.read_csv('/root/flight_results.csv')
        hold = results[(results['time'] >= 18.0) & (results['time'] <= 30.0)]
        assert hold['error'].abs().mean() < 0.45


class TestDescentPerformance:
    """Performance target for the descent-settle window."""

    def test_descent_performance(self):
        import pandas as pd

        results = pd.read_csv('/root/flight_results.csv')
        settle = results[(results['time'] >= 40.0) & (results['time'] <= 48.0)]
        assert settle['error'].abs().mean() < 0.35
        assert results['vertical_speed'].abs().max() <= 3.2
