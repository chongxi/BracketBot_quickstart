"""
Simple motor control library for differential drive robot.
Provides a toy-car-like API: forward, backward, left, right, stop.

Uses the native odrive library (same as test_wasd_stand.py).
Speed is in turns/sec (not m/s) to match ODrive native units.
"""

import odrive
from odrive.enums import (
    CONTROL_MODE_VELOCITY_CONTROL,
    INPUT_MODE_PASSTHROUGH,
    AXIS_STATE_CLOSED_LOOP_CONTROL,
    AXIS_STATE_IDLE,
)
import time


class Motor:
    """Simple interface for controlling a two-wheel differential drive robot."""

    def __init__(self, speed: float = 1.5, turn_speed: float = 0.5):
        """
        Initialize motor controller.

        Args:
            speed: Default forward/backward speed in turns/sec
            turn_speed: Default turning speed in turns/sec
        """
        self.speed = speed
        self.turn_speed = turn_speed
        self._odrv = None

    def start(self):
        """Connect to ODrive and start motors in velocity control mode."""
        print("Connecting to ODrive...")
        self._odrv = odrive.find_any(path="serial:/dev/ttyAMA1", timeout=10)
        if self._odrv is None:
            raise RuntimeError("Could not connect to ODrive")

        print(f"Connected! Bus voltage: {self._odrv.vbus_voltage:.1f}V")

        # Clear errors
        self._odrv.axis0.clear_errors()
        self._odrv.axis1.clear_errors()
        time.sleep(0.3)

        # Set velocity control mode
        self._odrv.axis0.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
        self._odrv.axis1.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
        self._odrv.axis0.controller.config.input_mode = INPUT_MODE_PASSTHROUGH
        self._odrv.axis1.controller.config.input_mode = INPUT_MODE_PASSTHROUGH

        # Start closed loop control
        self._odrv.axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        self._odrv.axis1.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        time.sleep(0.5)

        # Verify motors started
        if self._odrv.axis0.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
            raise RuntimeError(f"Axis 0 failed to start: {self._odrv.axis0.error}")
        if self._odrv.axis1.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
            raise RuntimeError(f"Axis 1 failed to start: {self._odrv.axis1.error}")

        # Set velocity ramp for smooth acceleration
        self.set_ramp_rate(0.5)

        # Reduce integrator gain to prevent overshoot when stopping
        self._tune_pid()

        # Print PID parameters
        self.print_pid()

        print("Motors ready!")

    def print_pid(self):
        """Print current PID parameters for both axes."""
        if not self._odrv:
            return
        print("PID parameters:")
        for i, axis in enumerate([self._odrv.axis0, self._odrv.axis1]):
            cfg = axis.controller.config
            print(f"  Axis{i}: vel_gain={cfg.vel_gain:.3f}, "
                  f"vel_integrator_gain={cfg.vel_integrator_gain:.3f}, "
                  f"vel_ramp_rate={cfg.vel_ramp_rate:.2f}")

    def _tune_pid(self):
        """Reduce vel_integrator_gain to prevent overshoot on stopping."""
        for axis in [self._odrv.axis0, self._odrv.axis1]:
            vel_gain = axis.controller.config.vel_gain
            # Use 0.3x of vel_gain (reduced from default ~5x ratio)
            axis.controller.config.vel_integrator_gain = vel_gain * 0.3

    def set_vel_gain(self, gain: float):
        """Set velocity P gain for both axes."""
        if self._odrv:
            self._odrv.axis0.controller.config.vel_gain = gain
            self._odrv.axis1.controller.config.vel_gain = gain

    def set_vel_integrator_gain(self, gain: float):
        """Set velocity I gain for both axes."""
        if self._odrv:
            self._odrv.axis0.controller.config.vel_integrator_gain = gain
            self._odrv.axis1.controller.config.vel_integrator_gain = gain

    def set_ramp_rate(self, rate: float):
        """Set velocity ramp rate (turns/sec^2) for smooth acceleration."""
        if self._odrv:
            self._odrv.axis0.controller.config.vel_ramp_rate = rate
            self._odrv.axis1.controller.config.vel_ramp_rate = rate

    def _set_velocity(self, left: float, right: float):
        """Set wheel velocities in turns/sec. Handles motor direction."""
        # axis0 is left motor (reversed), axis1 is right motor
        self._odrv.axis0.controller.input_vel = -left
        self._odrv.axis1.controller.input_vel = right

    def stop(self):
        """Stop both wheels immediately."""
        if self._odrv:
            self._odrv.axis0.controller.input_vel = 0
            self._odrv.axis1.controller.input_vel = 0
            # Reset velocity integrators to prevent drift after turning
            self._odrv.axis0.controller.vel_integrator_torque = 0
            self._odrv.axis1.controller.vel_integrator_torque = 0

    def shutdown(self):
        """Stop motors and set to idle."""
        if self._odrv:
            self.stop()
            time.sleep(0.2)
            self._odrv.axis0.requested_state = AXIS_STATE_IDLE
            self._odrv.axis1.requested_state = AXIS_STATE_IDLE

    def forward(self, speed: float = None):
        """Move forward."""
        s = speed if speed is not None else self.speed
        self._set_velocity(s, s)

    def backward(self, speed: float = None):
        """Move backward."""
        s = speed if speed is not None else self.speed
        self._set_velocity(-s, -s)

    def left(self, speed: float = None):
        """Turn left (spin in place)."""
        s = speed if speed is not None else self.turn_speed
        self._set_velocity(-s, s)

    def right(self, speed: float = None):
        """Turn right (spin in place)."""
        s = speed if speed is not None else self.turn_speed
        self._set_velocity(s, -s)

    @property
    def bus_voltage(self) -> float:
        """Get current bus voltage."""
        if self._odrv:
            return self._odrv.vbus_voltage
        return 0.0
