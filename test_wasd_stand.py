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

# ANSI colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def get_key():
    """Get a single keypress from the user."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

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
    print("Starting motors...")
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

    # Test speeds (in turns/sec - ODrive uses encoder counts)
    # Start with low speed for safety
    move_speed = 1.0  # turns per second for forward/backward
    turn_speed = 0.5  # turns per second for turning (slower)

    print(f"{YELLOW}Controls:{RESET}")
    print("  W - Forward    S - Backward")
    print("  A - Left       D - Right")
    print("  Q - Left only  E - Right only")
    print("  Z - Left back  C - Right back")
    print("  SPACE - Stop")
    print("  +/- - Increase/Decrease move speed")
    print("  [/] - Increase/Decrease turn speed")
    print("  ESC - Exit")
    print(f"\nMove speed: {YELLOW}{move_speed:.1f}{RESET} turns/sec")
    print(f"Turn speed: {YELLOW}{turn_speed:.1f}{RESET} turns/sec")
    print(f"{GREEN}Ready! Press keys to control...{RESET}\n")

    try:
        while True:
            key = get_key()

            if key == '\x1b':  # ESC
                break
            elif key == 'w' or key == 'W':
                print(f"↑ Forward ({move_speed:.1f} turns/sec)")
                odrv.axis0.controller.input_vel = -move_speed  # Left motor reversed
                odrv.axis1.controller.input_vel = move_speed
            elif key == 's' or key == 'S':
                print(f"↓ Backward ({move_speed:.1f} turns/sec)")
                odrv.axis0.controller.input_vel = move_speed   # Left motor reversed
                odrv.axis1.controller.input_vel = -move_speed
            elif key == 'a' or key == 'A':
                print(f"← Left turn ({turn_speed:.1f} turns/sec) - Differential")
                # turn_left in API: set_velocity(-speed, speed) → left back, right forward
                # With axis0 reversed: axis0=+turn_speed (goes back), axis1=+turn_speed (goes forward)
                odrv.axis0.controller.input_vel = turn_speed   # Left backward (reversed motor)
                odrv.axis1.controller.input_vel = turn_speed   # Right forward
            elif key == 'd' or key == 'D':
                print(f"→ Right turn ({turn_speed:.1f} turns/sec) - Differential")
                # turn_right in API: set_velocity(speed, -speed) → left forward, right back
                # With axis0 reversed: axis0=-turn_speed (goes forward), axis1=-turn_speed (goes back)
                odrv.axis0.controller.input_vel = -turn_speed  # Left forward (reversed motor)
                odrv.axis1.controller.input_vel = -turn_speed  # Right backward
            elif key == 'q' or key == 'Q':
                print(f"Left wheel forward ({move_speed:.1f} turns/sec)")
                odrv.axis0.controller.input_vel = -move_speed  # Left motor reversed
                odrv.axis1.controller.input_vel = 0
            elif key == 'e' or key == 'E':
                print(f"Right wheel forward ({move_speed:.1f} turns/sec)")
                odrv.axis0.controller.input_vel = 0
                odrv.axis1.controller.input_vel = move_speed
            elif key == 'z' or key == 'Z':
                print(f"Left wheel backward ({move_speed:.1f} turns/sec)")
                odrv.axis0.controller.input_vel = move_speed   # Left motor reversed
                odrv.axis1.controller.input_vel = 0
            elif key == 'c' or key == 'C':
                print(f"Right wheel backward ({move_speed:.1f} turns/sec)")
                odrv.axis0.controller.input_vel = 0
                odrv.axis1.controller.input_vel = -move_speed
            elif key == ' ':
                print("⏹ STOP")
                odrv.axis0.controller.input_vel = 0
                odrv.axis1.controller.input_vel = 0
            elif key == '+' or key == '=':
                move_speed = min(move_speed + 0.5, 10.0)
                print(f"Move speed: {YELLOW}{move_speed:.1f}{RESET} turns/sec")
            elif key == '-' or key == '_':
                move_speed = max(move_speed - 0.5, 0.5)
                print(f"Move speed: {YELLOW}{move_speed:.1f}{RESET} turns/sec")
            elif key == '[':
                turn_speed = min(turn_speed + 0.25, 5.0)
                print(f"Turn speed: {YELLOW}{turn_speed:.1f}{RESET} turns/sec")
            elif key == ']':
                turn_speed = max(turn_speed - 0.25, 0.25)
                print(f"Turn speed: {YELLOW}{turn_speed:.1f}{RESET} turns/sec")
            elif key == '\x03':  # Ctrl+C
                break

    except KeyboardInterrupt:
        pass
    finally:
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
