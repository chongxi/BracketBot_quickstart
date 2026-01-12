#!/usr/bin/env python3
"""
Simple WASD test script for ODrive wheel control on a stand.
This script lets you test wheel movement without calibration.

Controls:
  W - Both wheels forward
  S - Both wheels backward
  A - Left turn (left wheel back, right wheel forward)
  D - Right turn (left wheel forward, right wheel back)
  Q - Left wheel only forward
  E - Right wheel only forward
  Z - Left wheel only backward
  C - Right wheel only backward
  SPACE - Stop both wheels
  ESC or Ctrl+C - Exit

Note: This uses raw ODrive velocity control without calibration.
      Motors may not be perfectly tuned yet.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import odrive
from odrive.enums import *
import termios
import tty
import time
import select

# ANSI colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

class RawInput:
    """Context manager for raw terminal input with non-blocking reads."""
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = None

    def __enter__(self):
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)
        return self

    def __exit__(self, *args):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def get_key(self):
        """Non-blocking read, returns None if no key available."""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

    def get_key_blocking(self):
        """Blocking read, waits for a key."""
        return sys.stdin.read(1)

def main():
    print(f"{BLUE}=== ODrive WASD Test (On Stand) ==={RESET}\n")

    # Connect to ODrive
    print("Connecting to ODrive on /dev/ttyAMA1...")
    try:
        odrv = odrive.find_any(path='serial:/dev/ttyAMA1', timeout=10)
        if odrv is None:
            print(f"{RED}✗ Could not connect to ODrive{RESET}")
            return
    except Exception as e:
        print(f"{RED}✗ Error connecting: {e}{RESET}")
        return

    print(f"{GREEN}✅ Connected!{RESET}")
    print(f"   Bus voltage: {odrv.vbus_voltage:.2f}V\n")

    # Clear any errors
    print("Clearing errors...")
    odrv.axis0.clear_errors()
    odrv.axis1.clear_errors()
    time.sleep(0.5)

    # Set to velocity control mode
    print("Setting velocity control mode...")
    odrv.axis0.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
    odrv.axis1.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
    odrv.axis0.controller.config.input_mode = INPUT_MODE_PASSTHROUGH
    odrv.axis1.controller.config.input_mode = INPUT_MODE_PASSTHROUGH

    # Start motors in closed loop control
    # print("Starting motors...")
    odrv.axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
    odrv.axis1.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL

    time.sleep(1)

    # Check if motors started successfully
    if odrv.axis0.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
        print(f"{RED}✗ Axis 0 failed to start. State: {odrv.axis0.current_state}{RESET}")
        print(f"   Errors: {odrv.axis0.error}")
        return
    if odrv.axis1.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
        print(f"{RED}✗ Axis 1 failed to start. State: {odrv.axis1.current_state}{RESET}")
        print(f"   Errors: {odrv.axis1.error}")
        return

    print(f"{GREEN}✅ Motors started in closed loop control!{RESET}\n")

    # Set velocity ramping for smooth acceleration (prevents wheel slip)
    print("Setting velocity ramping for smooth control...")
    odrv.axis0.controller.config.vel_ramp_rate = 0.5  # turns/sec^2 (smooth acceleration)
    odrv.axis1.controller.config.vel_ramp_rate = 0.5

    odrv.axis0.controller.config.vel_gain = 1.5 # 2.3
    odrv.axis1.controller.config.vel_gain = 2.3 # 1.5

    odrv.axis0.controller.config.vel_integrator_gain = 4.5
    odrv.axis1.controller.config.vel_integrator_gain = 4.5

    # Show current PID gains
    print(f"\n{BLUE}Current PID gains:{RESET}")
    print(f"  Axis0 - vel_gain: {odrv.axis0.controller.config.vel_gain:.2f}, vel_integrator_gain: {odrv.axis0.controller.config.vel_integrator_gain:.2f}")
    print(f"  Axis1 - vel_gain: {odrv.axis1.controller.config.vel_gain:.2f}, vel_integrator_gain: {odrv.axis1.controller.config.vel_integrator_gain:.2f}")

    # Reduce vel_integrator_gain to reduce overshoot on stopping
    # ODrive docs recommend: integrator_gain should be ~equal or less than vel_gain
    # Current calibration uses 5x ratio (0.1 vs 0.02), which causes overshoot
    print(f"\n{YELLOW}Reducing vel_integrator_gain to reduce stopping overshoot...{RESET}")
    # for axis_num in [0, 1]:
    #     axis = getattr(odrv, f'axis{axis_num}')
    #     current_vel_gain = axis.controller.config.vel_gain
    #     # Reduce integrator gain to 2.0x of vel_gain (from 5x) to reduce overshoot
    #     new_integrator_gain = current_vel_gain * 0.3
    #     axis.controller.config.vel_integrator_gain = new_integrator_gain
    #     print(f"  Axis{axis_num}: vel_integrator_gain {axis.controller.config.vel_integrator_gain:.2f} -> {new_integrator_gain:.2f}")

    # Set current limits to prevent excessive torque
    print(f"\nCurrent limits - Axis0: {odrv.axis0.motor.config.current_lim}A, Axis1: {odrv.axis1.motor.config.current_lim}A")

    # Test speeds (in turns/sec - ODrive uses encoder counts)
    # Start with VERY low speed for stand testing to prevent wheel slip
    move_speed = 1.5  # turns per second for forward/backward (reduced from 1.0)
    turn_speed = 0.3  # turns per second for turning (reduced from 0.5)

    print(f"{YELLOW}Controls:{RESET}")
    print("  W - Forward    S - Backward")
    print("  A - Left       D - Right")
    print("  Q - Left only  E - Right only")
    print("  Z - Left back  C - Right back")
    print("  SPACE - Stop")
    print("  +/- - Increase/Decrease move speed")
    print("  [/] - Increase/Decrease turn speed")
    print("  (Speed display: actual/target in turns/sec)")
    print("  R - Adjust ramp rate")
    print("  ESC - Exit")
    print(f"\nMove speed: {YELLOW}{move_speed:.1f}{RESET} turns/sec")
    print(f"Turn speed: {YELLOW}{turn_speed:.1f}{RESET} turns/sec")
    print(f"{GREEN}Ready! Press keys to control...{RESET}\n")

    last_command = None  # Track the last movement command
    last_monitor_time = 0
    current_ramp_rate = 0.5  # Track current ramp rate
    status_msg = "STOP"  # Current command status

    with RawInput() as raw_input:
        try:
            while True:
                # Always display wheel speed at ~60Hz on two lines
                current_time = time.time()
                if (current_time - last_monitor_time) > 0.016:  # ~60Hz update
                    vel0 = odrv.axis0.encoder.vel_estimate
                    vel1 = odrv.axis1.encoder.vel_estimate
                    input0 = odrv.axis0.controller.input_vel
                    input1 = odrv.axis1.controller.input_vel
                    # Use ANSI escape to show status on line above speed
                    # \033[2K clears line, \033[A moves up, \r returns to start
                    # Fwd = -vel0 + vel1 (positive=forward, since L is negated)
                    # Steer = vel0 + vel1 (positive=turning left, negative=turning right)
                    fwd = -vel0 + vel1
                    steer = vel0 + vel1
                    sys.stdout.write(f"\r\033[K{YELLOW}[Cmd]{RESET} {status_msg}\n")
                    sys.stdout.write(f"\r\033[K{BLUE}[Speed]{RESET} L:{vel0:+.2f} R:{vel1:+.2f} | Fwd:{fwd:+.2f} Steer:{steer:+.2f}\033[A")
                    sys.stdout.flush()
                    last_monitor_time = current_time

                key = raw_input.get_key()

                if key is None:
                    time.sleep(0.001)  # Small sleep to prevent CPU spinning
                    continue
                elif key == '\x1b':  # ESC
                    break
                elif key == 'w' or key == 'W':
                    last_command = 'w'
                    status_msg = f"↑ Forward ({move_speed:.1f} t/s)"
                    odrv.axis0.controller.input_vel = -move_speed  # Left motor reversed
                    odrv.axis1.controller.input_vel = move_speed
                elif key == 's' or key == 'S':
                    last_command = 's'
                    status_msg = f"↓ Backward ({move_speed:.1f} t/s)"
                    odrv.axis0.controller.input_vel = move_speed   # Left motor reversed
                    odrv.axis1.controller.input_vel = -move_speed
                elif key == 'a' or key == 'A':
                    last_command = 'a'
                    status_msg = f"← Left turn ({turn_speed:.1f} t/s)"
                    odrv.axis0.controller.input_vel = turn_speed   # Left backward (reversed motor)
                    odrv.axis1.controller.input_vel = turn_speed   # Right forward
                elif key == 'd' or key == 'D':
                    last_command = 'd'
                    status_msg = f"→ Right turn ({turn_speed:.1f} t/s)"
                    odrv.axis0.controller.input_vel = -turn_speed  # Left forward (reversed motor)
                    odrv.axis1.controller.input_vel = -turn_speed  # Right backward
                elif key == 'e' or key == 'E':
                    last_command = 'e'
                    status_msg = f"Left wheel fwd ({move_speed:.1f} t/s)"
                    odrv.axis0.controller.input_vel = -move_speed  # Left motor reversed
                    odrv.axis1.controller.input_vel = 0
                elif key == 'q' or key == 'Q':
                    last_command = 'q'
                    status_msg = f"Right wheel fwd ({move_speed:.1f} t/s)"
                    odrv.axis0.controller.input_vel = 0
                    odrv.axis1.controller.input_vel = move_speed
                elif key == 'z' or key == 'Z':
                    last_command = 'z'
                    status_msg = f"Left wheel back ({move_speed:.1f} t/s)"
                    odrv.axis0.controller.input_vel = move_speed   # Left motor reversed
                    odrv.axis1.controller.input_vel = 0
                elif key == 'c' or key == 'C':
                    last_command = 'c'
                    status_msg = f"Right wheel back ({move_speed:.1f} t/s)"
                    odrv.axis0.controller.input_vel = 0
                    odrv.axis1.controller.input_vel = -move_speed
                elif key == ' ':
                    last_command = None
                    status_msg = "⏹ STOP"
                    odrv.axis0.controller.input_vel = 0
                    odrv.axis1.controller.input_vel = 0
                    # Reset the velocity integrators to prevent residual rotation
                    odrv.axis0.controller.vel_integrator_torque = 0
                    odrv.axis1.controller.vel_integrator_torque = 0
                elif key == '+' or key == '=':
                    move_speed = min(move_speed + 0.5, 10.0)
                    status_msg = f"Move speed: {move_speed:.1f} t/s"
                    # Re-apply last command with new speed
                    if last_command == 'w':
                        odrv.axis0.controller.input_vel = -move_speed
                        odrv.axis1.controller.input_vel = move_speed
                        status_msg = f"↑ Forward ({move_speed:.1f} t/s)"
                    elif last_command == 's':
                        odrv.axis0.controller.input_vel = move_speed
                        odrv.axis1.controller.input_vel = -move_speed
                        status_msg = f"↓ Backward ({move_speed:.1f} t/s)"
                elif key == '-' or key == '_':
                    move_speed = max(move_speed - 0.5, 0.5)
                    status_msg = f"Move speed: {move_speed:.1f} t/s"
                    # Re-apply last command with new speed
                    if last_command == 'w':
                        odrv.axis0.controller.input_vel = -move_speed
                        odrv.axis1.controller.input_vel = move_speed
                        status_msg = f"↑ Forward ({move_speed:.1f} t/s)"
                    elif last_command == 's':
                        odrv.axis0.controller.input_vel = move_speed
                        odrv.axis1.controller.input_vel = -move_speed
                        status_msg = f"↓ Backward ({move_speed:.1f} t/s)"
                elif key == '[':
                    turn_speed = min(turn_speed + 0.25, 5.0)
                    status_msg = f"Turn speed: {turn_speed:.1f} t/s"
                    # Re-apply last command with new speed
                    if last_command == 'a':
                        odrv.axis0.controller.input_vel = turn_speed
                        odrv.axis1.controller.input_vel = turn_speed
                        status_msg = f"← Left turn ({turn_speed:.1f} t/s)"
                    elif last_command == 'd':
                        odrv.axis0.controller.input_vel = -turn_speed
                        odrv.axis1.controller.input_vel = -turn_speed
                        status_msg = f"→ Right turn ({turn_speed:.1f} t/s)"
                elif key == ']':
                    turn_speed = max(turn_speed - 0.25, 0.25)
                    status_msg = f"Turn speed: {turn_speed:.1f} t/s"
                    # Re-apply last command with new speed
                    if last_command == 'a':
                        odrv.axis0.controller.input_vel = turn_speed
                        odrv.axis1.controller.input_vel = turn_speed
                        status_msg = f"← Left turn ({turn_speed:.1f} t/s)"
                    elif last_command == 'd':
                        odrv.axis0.controller.input_vel = -turn_speed
                        odrv.axis1.controller.input_vel = -turn_speed
                        status_msg = f"→ Right turn ({turn_speed:.1f} t/s)"
                elif key == 'r' or key == 'R':
                    status_msg = f"Ramp: 1=0.5 2=1.0 3=2.0 4=5.0 5=10.0"
                    ramp_key = raw_input.get_key_blocking()
                    ramp_options = {'1': 0.5, '2': 1.0, '3': 2.0, '4': 5.0, '5': 10.0}
                    if ramp_key in ramp_options:
                        current_ramp_rate = ramp_options[ramp_key]
                        odrv.axis0.controller.config.vel_ramp_rate = current_ramp_rate
                        odrv.axis1.controller.config.vel_ramp_rate = current_ramp_rate
                        status_msg = f"Ramp rate: {current_ramp_rate} t/s²"
                    else:
                        status_msg = "Ramp unchanged"
                elif key == '\x03':  # Ctrl+C
                    break

        except KeyboardInterrupt:
            pass

    # Cleanup (outside the with block so terminal is restored)
    print(f"\n{YELLOW}Stopping motors...{RESET}")
    odrv.axis0.controller.input_vel = 0
    odrv.axis1.controller.input_vel = 0
    time.sleep(0.5)

    print("Setting motors to idle...")
    odrv.axis0.requested_state = AXIS_STATE_IDLE
    odrv.axis1.requested_state = AXIS_STATE_IDLE

    print(f"{GREEN}✅ Test complete!{RESET}")

if __name__ == "__main__":
    main()
