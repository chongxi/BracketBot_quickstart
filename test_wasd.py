#!/usr/bin/env python3
"""
Simple WASD control - like a toy car.
Hold a key to move, release to stop.

Controls:
  W - Forward
  S - Backward
  A - Turn Left
  D - Turn Right
  Q - Quit
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from sshkeyboard import listen_keyboard, stop_listening
from lib.motor import Motor


# =============================================================================
# CONFIGURATION - Adjust these parameters
# =============================================================================
SPEED = 2.0           # Forward/backward speed (turns/sec)
TURN_SPEED = 1.0      # Turning speed (turns/sec)
RAMP_RATE = 0.5       # Acceleration rate (turns/sec^2), higher = snappier
VEL_GAIN = 2       # Velocity P gain (None = use calibrated value)
VEL_INTEGRATOR_GAIN = 1  # Velocity I gain (None = 0.3 * vel_gain)
# =============================================================================


def main():
    motor = Motor(speed=SPEED, turn_speed=TURN_SPEED)

    def on_press(key):
        k = key.lower()
        if k == 'w':
            motor.forward()
        elif k == 's':
            motor.backward()
        elif k == 'a':
            motor.left()
        elif k == 'd':
            motor.right()
        elif k == 'q':
            stop_listening()

    def on_release(key):
        motor.stop()

    print("=== WASD Control ===")
    print("Controls:")
    print("  W - Forward")
    print("  S - Backward")
    print("  A - Turn Left")
    print("  D - Turn Right")
    print("  Q - Quit")
    print("\nHold key to move, release to stop.\n")

    motor.start()

    # Apply custom parameters if set
    if RAMP_RATE is not None:
        motor.set_ramp_rate(RAMP_RATE)
    if VEL_GAIN is not None:
        motor.set_vel_gain(VEL_GAIN)
    if VEL_INTEGRATOR_GAIN is not None:
        motor.set_vel_integrator_gain(VEL_INTEGRATOR_GAIN)

    # Show final parameters
    motor.print_pid()

    try:
        listen_keyboard(
            on_press=on_press,
            on_release=on_release,
            delay_second_char=0.05,
            delay_other_chars=0.02,
            sequential=False,
            sleep=0.01
        )
    except KeyboardInterrupt:
        pass
    finally:
        print("\nShutting down...")
        motor.shutdown()
        print("Done.")


if __name__ == "__main__":
    main()
