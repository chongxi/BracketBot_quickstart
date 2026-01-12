#!/usr/bin/env python3
"""Simple test script to capture images from USB camera

Usage:
    python test_usb_camera.py [device]

Examples:
    python test_usb_camera.py        # Use default /dev/video0
    python test_usb_camera.py 4      # Use /dev/video4 (RealSense RGB)
"""

import cv2
import os
import sys
import time

# Parse device argument
device = int(sys.argv[1]) if len(sys.argv) > 1 else 0

# Create img folder if it doesn't exist
os.makedirs("img", exist_ok=True)

# Open the USB camera
print(f"Opening /dev/video{device}...")
cap = cv2.VideoCapture(device)

if not cap.isOpened():
    print("Error: Could not open camera")
    exit(1)

print("Camera opened successfully")

# Set buffer size to 1 for minimum latency
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# Try to fix white balance - enable auto white balance
cap.set(cv2.CAP_PROP_AUTO_WB, 1)  # Enable auto white balance
cap.set(cv2.CAP_PROP_WB_TEMPERATURE, 4500)  # Set white balance temperature (daylight ~5500, tungsten ~3200)

print(f"Buffer size: {cap.get(cv2.CAP_PROP_BUFFERSIZE)}")

print("Waiting 3 seconds for camera to adjust white balance...")
time.sleep(3)

# Discard a few frames to let auto-exposure and white balance settle
for _ in range(10):
    cap.read()

# Capture 3 images with latency measurement
print("\nLatency test:")
for i in range(3):
    t_start = time.perf_counter()
    ret, frame = cap.read()
    t_capture = time.perf_counter()
    if ret:
        filename = f"img/test_{i+1}.jpg"
        cv2.imwrite(filename, frame)
        t_save = time.perf_counter()

        capture_ms = (t_capture - t_start) * 1000
        save_ms = (t_save - t_capture) * 1000
        total_ms = (t_save - t_start) * 1000
        print(f"{filename} - Capture: {capture_ms:.1f}ms, Save: {save_ms:.1f}ms, Total: {total_ms:.1f}ms")
    else:
        print(f"Failed to capture image {i+1}")
    time.sleep(0.5)

cap.release()
print("Done! Check the img folder for the captured images.")
