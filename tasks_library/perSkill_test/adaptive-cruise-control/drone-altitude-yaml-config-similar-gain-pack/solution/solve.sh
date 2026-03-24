#!/bin/bash

python3 <<'PYTHON_SCRIPT'
import textwrap
import yaml


altitude_controller_code = textwrap.dedent(
    '''\
    """PID controller for the drone altitude loop."""


    class PIDController:
        """Discrete PID controller with light anti-windup."""

        def __init__(self, kp, ki, kd):
            self.kp = kp
            self.ki = ki
            self.kd = kd
            self.integral = 0.0
            self.prev_error = None

        def reset(self):
            self.integral = 0.0
            self.prev_error = None

        def compute(self, error, dt):
            if dt <= 0:
                return 0.0

            self.integral += error * dt
            self.integral = max(-10.0, min(10.0, self.integral))

            derivative = 0.0
            if self.prev_error is not None:
                derivative = (error - self.prev_error) / dt
            self.prev_error = error

            return (
                self.kp * error
                + self.ki * self.integral
                + self.kd * derivative
            )
    '''
)

altitude_hold_code = textwrap.dedent(
    '''\
    """Altitude-hold logic for a simple 1D drone model."""

    from altitude_controller import PIDController


    class AltitudeHoldController:
        """Computes thrust commands from altitude error and vertical speed."""

        def __init__(self, config):
            drone = config['drone']
            controller = config['controller']

            self.mass = drone['mass_kg']
            self.hover_thrust = drone['thrust']['hover_newton']
            self.min_thrust = drone['thrust']['min_newton']
            self.max_thrust = drone['thrust']['max_newton']
            self.damping_gain = controller['vertical_damping']['gain']

            pid_config = controller['altitude_hold']['pid']
            self.pid = PIDController(
                kp=pid_config['kp'],
                ki=pid_config['ki'],
                kd=pid_config['kd'],
            )

        def compute(self, target_altitude, altitude, vertical_speed, dt):
            altitude_error = target_altitude - altitude
            accel_request = self.pid.compute(altitude_error, dt)
            accel_request -= self.damping_gain * vertical_speed

            thrust_cmd = self.hover_thrust + self.mass * accel_request
            thrust_cmd = max(self.min_thrust, min(self.max_thrust, thrust_cmd))

            return thrust_cmd, altitude_error
    '''
)

run_flight_code = textwrap.dedent(
    '''\
    """Run the drone altitude-hold simulation from YAML and telemetry inputs."""

    import yaml
    import pandas as pd

    from altitude_hold import AltitudeHoldController


    CONFIG_PATH = '/root/flight_params.yaml'
    TELEMETRY_PATH = '/root/telemetry.csv'
    TUNING_PATH = '/root/altitude_tuning.yaml'
    RESULTS_PATH = '/root/flight_results.csv'
    REPORT_PATH = '/root/altitude_report.md'


    def load_yaml(path):
        with open(path, 'r', encoding='utf-8') as handle:
            return yaml.safe_load(handle)


    def apply_tuning(config, tuning):
        loop = tuning['altitude_loop']
        config['controller']['altitude_hold']['pid'] = {
            'kp': loop['kp'],
            'ki': loop['ki'],
            'kd': loop['kd'],
        }
        config['controller']['vertical_damping']['gain'] = loop['damping_gain']
        return config


    def run_simulation():
        config = load_yaml(CONFIG_PATH)
        tuning = load_yaml(TUNING_PATH)
        telemetry = pd.read_csv(TELEMETRY_PATH)
        config = apply_tuning(config, tuning)

        controller = AltitudeHoldController(config)

        dt = config['mission']['dt']
        mass = config['drone']['mass_kg']
        hover = config['drone']['thrust']['hover_newton']
        drag = config['drone']['drag']['vertical_damping']
        safety = config['mission']['safety']

        altitude = config['initial_state']['altitude_m']
        vertical_speed = config['initial_state']['vertical_speed_mps']

        rows = []
        for row in telemetry.itertuples(index=False):
            thrust_cmd, _ = controller.compute(
                target_altitude=row.target_altitude,
                altitude=altitude,
                vertical_speed=vertical_speed,
                dt=dt,
            )

            accel = (thrust_cmd - hover) / mass + row.wind_accel - drag * vertical_speed
            accel = max(-safety['max_accel_mps2'], min(safety['max_accel_mps2'], accel))

            vertical_speed += accel * dt
            vertical_speed = max(
                safety['max_descent_rate_mps'],
                min(safety['max_climb_rate_mps'], vertical_speed),
            )

            altitude += vertical_speed * dt
            altitude = max(safety['min_altitude_m'], altitude)

            rows.append(
                {
                    'time': row.time,
                    'target_altitude': row.target_altitude,
                    'altitude': altitude,
                    'vertical_speed': vertical_speed,
                    'thrust_cmd': thrust_cmd,
                    'error': row.target_altitude - altitude,
                    'phase': row.phase,
                }
            )

        results = pd.DataFrame(rows)
        results.to_csv(RESULTS_PATH, index=False)
        write_report(results, tuning)
        return results


    def write_report(results, tuning):
        climb = results[(results['time'] >= 5.0) & (results['time'] <= 18.0)]
        hold = results[(results['time'] >= 18.0) & (results['time'] <= 30.0)]
        settle = results[(results['time'] >= 40.0) & (results['time'] <= 48.0)]

        rise_start = climb[climb['altitude'] >= 2.55]['time'].min()
        rise_end = climb[climb['altitude'] >= 10.95]['time'].min()
        rise_time = rise_end - rise_start
        overshoot = climb['altitude'].max() - 12.0
        hold_mae = hold['error'].abs().mean()
        settle_mae = settle['error'].abs().mean()

        report = f"""# Altitude Report

    ## System design
    The simulation uses a single altitude PID loop plus vertical-speed damping.
    Runtime configuration is read from nested YAML, then the tuned gains are applied before the flight loop starts.

    ## Gain tuning methodology and final gains
    The final gains focus on a fast climb with limited overshoot while staying stable through the gust segment.
    Final altitude loop: kp={tuning['altitude_loop']['kp']}, ki={tuning['altitude_loop']['ki']}, kd={tuning['altitude_loop']['kd']}, damping_gain={tuning['altitude_loop']['damping_gain']}.

    ## Flight results and performance metrics
    Climb rise time: {rise_time:.2f} s
    Climb overshoot: {overshoot:.3f} m
    Hold-window mean absolute error: {hold_mae:.3f} m
    Descent-settle mean absolute error: {settle_mae:.3f} m
    """

        with open(REPORT_PATH, 'w', encoding='utf-8') as handle:
            handle.write(report)


    if __name__ == '__main__':
        run_simulation()
    '''
)

with open('/root/altitude_controller.py', 'w', encoding='utf-8') as handle:
    handle.write(altitude_controller_code)

with open('/root/altitude_hold.py', 'w', encoding='utf-8') as handle:
    handle.write(altitude_hold_code)

with open('/root/run_flight.py', 'w', encoding='utf-8') as handle:
    handle.write(run_flight_code)

tuning = {
    'altitude_loop': {
        'kp': 2.5,
        'ki': 0.0,
        'kd': 1.0,
        'damping_gain': 1.0,
    }
}

with open('/root/altitude_tuning.yaml', 'w', encoding='utf-8') as handle:
    yaml.dump(tuning, handle, default_flow_style=False, sort_keys=False)
PYTHON_SCRIPT

python3 /root/run_flight.py
