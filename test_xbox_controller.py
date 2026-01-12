#!/usr/bin/env python3
"""
Xbox Controller Test Script for Raspberry Pi 5

This script tests Xbox controller input via Bluetooth or USB.
It displays all button presses and joystick movements in real-time.

Requirements:
  pip install pygame

Pairing Xbox Controller via Bluetooth:
  1. Put controller in pairing mode: Hold Xbox button until it blinks rapidly
  2. On Pi: bluetoothctl
  3. > scan on
  4. > pair <controller_mac_address>
  5. > connect <controller_mac_address>
  6. > trust <controller_mac_address>

Or just plug in via USB cable.
"""

import sys

try:
    import pygame
except ImportError:
    print("pygame not installed. Install with: pip install pygame")
    sys.exit(1)

# ANSI colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'

def main():
    print(f"{BLUE}=== Xbox Controller Test ==={RESET}\n")

    # Initialize pygame and joystick module
    pygame.init()
    pygame.joystick.init()

    # Check for connected controllers
    joystick_count = pygame.joystick.get_count()

    if joystick_count == 0:
        print(f"{RED}No controller detected!{RESET}")
        print("\nTroubleshooting:")
        print("  USB: Make sure the controller is plugged in")
        print("  Bluetooth: Make sure controller is paired and connected")
        print("    1. Hold Xbox button until it blinks rapidly")
        print("    2. Run: bluetoothctl")
        print("    3. > scan on")
        print("    4. > pair <MAC>  (look for 'Xbox Wireless Controller')")
        print("    5. > connect <MAC>")
        print("    6. > trust <MAC>")
        pygame.quit()
        return

    print(f"{GREEN}Found {joystick_count} controller(s)!{RESET}\n")

    # Initialize the first controller
    controller = pygame.joystick.Joystick(0)
    controller.init()

    print(f"Controller: {CYAN}{controller.get_name()}{RESET}")
    print(f"  Axes: {controller.get_numaxes()}")
    print(f"  Buttons: {controller.get_numbuttons()}")
    print(f"  Hats (D-pad): {controller.get_numhats()}")

    print(f"\n{YELLOW}Press buttons and move joysticks to test...{RESET}")
    print(f"Press {RED}Ctrl+C{RESET} to exit\n")

    # Xbox controller button mapping (may vary by controller model)
    button_names = {
        0: "A",
        1: "B",
        2: "X",
        3: "Y",
        4: "LB",
        5: "RB",
        6: "Back/View",
        7: "Start/Menu",
        8: "Xbox",
        9: "L3 (Left Stick)",
        10: "R3 (Right Stick)",
    }

    # Xbox controller axis mapping
    axis_names = {
        0: "Left Stick X",
        1: "Left Stick Y",
        2: "Right Stick X",
        3: "Right Stick Y",
        4: "LT (Left Trigger)",
        5: "RT (Right Trigger)",
    }

    clock = pygame.time.Clock()

    try:
        while True:
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    btn_name = button_names.get(event.button, f"Button {event.button}")
                    print(f"{GREEN}[PRESSED]{RESET}  {btn_name}")

                elif event.type == pygame.JOYBUTTONUP:
                    btn_name = button_names.get(event.button, f"Button {event.button}")
                    print(f"{RED}[RELEASED]{RESET} {btn_name}")

                elif event.type == pygame.JOYAXISMOTION:
                    # Only print if axis moved significantly (deadzone)
                    if abs(event.value) > 0.1:
                        axis_name = axis_names.get(event.axis, f"Axis {event.axis}")
                        bar_len = int(abs(event.value) * 10)
                        bar = "█" * bar_len + "░" * (10 - bar_len)
                        direction = "+" if event.value > 0 else "-"
                        print(f"{BLUE}[AXIS]{RESET}     {axis_name}: {direction}{bar} ({event.value:+.2f})")

                elif event.type == pygame.JOYHATMOTION:
                    # D-pad
                    x, y = event.value
                    directions = []
                    if y == 1: directions.append("Up")
                    if y == -1: directions.append("Down")
                    if x == -1: directions.append("Left")
                    if x == 1: directions.append("Right")
                    if directions:
                        print(f"{CYAN}[D-PAD]{RESET}    {' + '.join(directions)}")
                    else:
                        print(f"{CYAN}[D-PAD]{RESET}    Released")

            # Limit update rate
            clock.tick(60)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Exiting...{RESET}")
    finally:
        pygame.quit()
        print(f"{GREEN}Done!{RESET}")

if __name__ == "__main__":
    main()
