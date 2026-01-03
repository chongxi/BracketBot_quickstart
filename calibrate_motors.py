#!/usr/bin/env python3
"""
Simplified motor calibration for ODrive - can run on a stand!
This only calibrates the motors and encoders without testing directions.

This file:
1. Connect to ODrive on /dev/ttyAMA1
2. Configure axis 0 (motor, encoder and controller settings)
3. Calibrate axis 0 (you will see wheel spin, for motor and encoder calibration)
4. Configure axis 1 (motor, encoder and controller settings)
5. Calibrate axis 1 (you will see wheel spin, for motor and encoder calibration)    
6. Save all settings and reboot ODrive
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'setup'))

import time
import odrive
from odrive.enums import *

# Colors
BLUE = '\033[94m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

def connect_odrive(timeout=30):
    print("Connecting to ODrive...")
    odrv = odrive.find_any(path='serial:/dev/ttyAMA1', timeout=timeout)
    if odrv is None:
        raise Exception('ODrive timed out')
    return odrv

def wait_for_idle(axis):
    while axis.current_state != AXIS_STATE_IDLE:
        time.sleep(0.1)

def save_and_reboot(odrv):
    print("Saving configuration...")
    try:
        odrv.save_configuration()
        print("Configuration saved successfully.")

        print("Rebooting ODrive...")
        try:
            odrv.reboot()
        except:
            pass  # Connection lost during reboot

        print(f"{GREEN}✓ Reboot command sent{RESET}")
        return True

    except Exception as e:
        print(f"Error saving configuration: {str(e)}")
        return False

def print_errors(error_type, error_value):
    if error_value == 0:
        return
    error_dict = {name: value for name, value in vars(odrive.enums).items()
                 if name.startswith(f'{error_type.upper()}_ERROR')}

    error_string = ""
    for error_name, error_code in error_dict.items():
        if error_value & error_code:
            error_string += f"{error_name.replace(f'{error_type.upper()}_ERROR_', '').lower().replace('_', ' ')}, "
    error_string = error_string.rstrip(", ")
    print(f"{RED}{error_type.capitalize()} error {hex(error_value)}: {error_string}{RESET}")

def calibrate_axis(odrv, axis):
    print(f"\n{BLUE}=== Calibrating Axis {axis} ==={RESET}")

    # Clear errors
    print("Clearing errors...")
    getattr(odrv, f'axis{axis}').clear_errors()
    time.sleep(1)

    # Check for errors
    axis_obj = getattr(odrv, f'axis{axis}')
    if axis_obj.error or axis_obj.motor.error or axis_obj.encoder.error:
        print(f"{RED}Axis {axis} has errors:{RESET}")
        print_errors('axis', axis_obj.error)
        print_errors('motor', axis_obj.motor.error)
        print_errors('encoder', axis_obj.encoder.error)
        return odrv, False

    # Motor configuration
    print("Configuring motor parameters...")
    axis_obj.motor.config.calibration_current = 5
    axis_obj.motor.config.pole_pairs = 15
    axis_obj.motor.config.resistance_calib_max_voltage = 4
    axis_obj.motor.config.requested_current_range = 25  # Requires config save and reboot
    axis_obj.motor.config.current_control_bandwidth = 100
    axis_obj.motor.config.torque_constant = 8.27 / 16.0

    # Encoder configuration
    print("Configuring encoder...")
    axis_obj.encoder.config.mode = ENCODER_MODE_HALL
    axis_obj.encoder.config.cpr = 90  # 6 poles * 15 pole pairs
    axis_obj.encoder.config.calib_scan_distance = 150
    axis_obj.encoder.config.bandwidth = 100

    # Controller configuration
    print("Configuring controller...")
    axis_obj.controller.config.pos_gain = 1
    axis_obj.controller.config.vel_gain = 0.02 * axis_obj.motor.config.torque_constant * axis_obj.encoder.config.cpr
    axis_obj.controller.config.vel_integrator_gain = 0.1 * axis_obj.motor.config.torque_constant * axis_obj.encoder.config.cpr
    axis_obj.controller.config.vel_limit = 10  # turns/sec
    axis_obj.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL

    # Motor calibration
    print(f"{YELLOW}Starting motor calibration... (wheels will spin briefly){RESET}")
    axis_obj.requested_state = AXIS_STATE_MOTOR_CALIBRATION

    # Wait for calibration
    while axis_obj.current_state == AXIS_STATE_MOTOR_CALIBRATION:
        time.sleep(0.1)

    wait_for_idle(axis_obj)

    # Check for errors
    if axis_obj.error:
        print(f"{RED}Motor calibration failed!{RESET}")
        print_errors('axis', axis_obj.error)
        print_errors('motor', axis_obj.motor.error)
        return odrv, False

    print(f"{GREEN}✓ Motor calibration successful{RESET}")

    # Encoder offset calibration
    print(f"{YELLOW}Starting encoder offset calibration... (wheels will spin){RESET}")
    axis_obj.requested_state = AXIS_STATE_ENCODER_OFFSET_CALIBRATION

    # Wait for calibration
    while axis_obj.current_state == AXIS_STATE_ENCODER_OFFSET_CALIBRATION:
        time.sleep(0.1)

    wait_for_idle(axis_obj)

    # Check for errors
    if axis_obj.error:
        print(f"{RED}Encoder calibration failed!{RESET}")
        print_errors('axis', axis_obj.error)
        print_errors('encoder', axis_obj.encoder.error)
        return odrv, False

    print(f"{GREEN}✓ Encoder calibration successful{RESET}")

    # Save calibration
    print("Saving calibration to ODrive...")
    axis_obj.encoder.config.pre_calibrated = True
    axis_obj.motor.config.pre_calibrated = True

    # Test closed loop control
    print(f"{YELLOW}Testing closed loop control...{RESET}")
    axis_obj.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
    time.sleep(1)

    if axis_obj.current_state != AXIS_STATE_CLOSED_LOOP_CONTROL:
        print(f"{RED}Failed to enter closed loop control!{RESET}")
        print_errors('axis', axis_obj.error)
        return odrv, False

    print(f"{GREEN}✓ Closed loop control working{RESET}")

    # Set to velocity control mode
    axis_obj.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL

    # Test velocity command
    print("Testing velocity command (wheel will spin briefly)...")
    axis_obj.controller.input_vel = 0.5
    time.sleep(2)
    axis_obj.controller.input_vel = 0
    time.sleep(1)

    # Back to idle
    axis_obj.requested_state = AXIS_STATE_IDLE
    time.sleep(0.5)

    print(f"{GREEN}✓ Axis {axis} calibration complete!{RESET}")
    return True

def main():
    print(f"{BLUE}{'='*50}")
    print("  ODrive Motor Calibration (Stand Mode)")
    print(f"{'='*50}{RESET}\n")

    print(f"{YELLOW}IMPORTANT: Place robot on stand with wheels FREE to spin!{RESET}")
    response = input("Are the wheels free to spin? (yes/no): ")
    if response.lower() != 'yes':
        print("Please place robot on stand and try again.")
        return

    print("\nConnecting to ODrive...")
    try:
        odrv = connect_odrive()
    except Exception as e:
        print(f"{RED}Failed to connect: {e}{RESET}")
        return

    print(f"{GREEN}✓ Connected!{RESET}")
    print(f"  Serial: {odrv.serial_number}")
    print(f"  Voltage: {odrv.vbus_voltage:.2f}V")

    # Calibrate both axes
    for axis_num in [0, 1]:
        success = calibrate_axis(odrv, axis_num)
        if not success:
            print(f"\n{RED}Calibration failed for axis {axis_num}!{RESET}")
            print("Please fix the errors and try again.")
            return

    # Save final configuration and reboot
    print(f"\n{YELLOW}Saving final configuration and rebooting...{RESET}")
    if save_and_reboot(odrv):
        print(f"\n{GREEN}{'='*50}")
        print("  ✓ Motor Calibration Complete!")
        print(f"{'='*50}{RESET}\n")

        print(f"{YELLOW}ODrive is rebooting...{RESET}")
        print("Wait about 10-15 seconds, then you can:")
        print("  1. Test the motors with: python test_wasd_stand.py")
        print("  2. Motor directions are set to default (both forward)")
        print("     If directions are wrong, we can fix them later")
    else:
        print(f"\n{RED}Failed to save configuration{RESET}")

if __name__ == '__main__':
    main()
