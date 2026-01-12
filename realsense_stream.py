#!/usr/bin/env python3
"""Flask app to stream RealSense D415 RGB + Depth over HTTP

Usage:
    python realsense_stream.py [rgb_device] [depth_device]

Examples:
    python realsense_stream.py              # Use defaults (video4 RGB, video0 depth)
    python realsense_stream.py 4 0          # Explicit devices
"""

import cv2
from flask import Flask, Response
import threading
import time
import sys
import numpy as np

app = Flask(__name__)

# Parse device arguments
rgb_device = int(sys.argv[1]) if len(sys.argv) > 1 else 4
depth_device = int(sys.argv[2]) if len(sys.argv) > 2 else 0

# Global variables for thread-safe camera access
output_frame = None
lock = threading.Lock()

# Depth range in mm (D415 typical range)
DEPTH_MIN = 200    # 20cm
DEPTH_MAX = 5000   # 5m


def depth_to_colormap(depth_raw):
    """Convert raw 16-bit depth to colorized image.

    D415 depth is in Z16 format (16-bit unsigned, values in mm).
    """
    # Clip to valid range
    depth_clipped = np.clip(depth_raw, DEPTH_MIN, DEPTH_MAX)

    # Normalize to 0-255
    depth_normalized = ((depth_clipped - DEPTH_MIN) / (DEPTH_MAX - DEPTH_MIN) * 255).astype(np.uint8)

    # Apply colormap (TURBO gives good depth visualization)
    depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_TURBO)

    return depth_colored


def camera_thread():
    """Continuously capture frames from both cameras"""
    global output_frame

    # Open RGB camera
    print(f"Opening RGB: /dev/video{rgb_device}...")
    cap_rgb = cv2.VideoCapture(rgb_device)
    cap_rgb.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap_rgb.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap_rgb.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap_rgb.set(cv2.CAP_PROP_FPS, 30)
    print(f"RGB opened: {cap_rgb.isOpened()}")

    # Open Depth camera
    print(f"Opening Depth: /dev/video{depth_device}...")
    cap_depth = cv2.VideoCapture(depth_device)
    cap_depth.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap_depth.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap_depth.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap_depth.set(cv2.CAP_PROP_FPS, 30)
    # Set format to Z16 (16-bit depth)
    cap_depth.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Z', '1', '6', ' '))
    print(f"Depth opened: {cap_depth.isOpened()}")

    # Warm up
    time.sleep(1)
    for _ in range(10):
        cap_rgb.read()
        cap_depth.read()

    print("Streaming started...")

    while True:
        # Capture RGB
        ret_rgb, frame_rgb = cap_rgb.read()
        if not ret_rgb:
            continue

        # Capture Depth
        ret_depth, frame_depth = cap_depth.read()
        if not ret_depth:
            # If depth fails, just show RGB with blank depth
            depth_colored = np.zeros_like(frame_rgb)
        else:
            # Convert depth frame to 16-bit
            # OpenCV may read it as 8-bit, need to handle both cases
            if frame_depth.dtype == np.uint8:
                # If read as BGR, convert to grayscale and interpret as 16-bit
                if len(frame_depth.shape) == 3:
                    # Take first two channels as low/high bytes
                    depth_raw = frame_depth[:, :, 0].astype(np.uint16) + \
                                (frame_depth[:, :, 1].astype(np.uint16) << 8)
                else:
                    depth_raw = frame_depth.astype(np.uint16)
            else:
                depth_raw = frame_depth

            # Ensure 2D array
            if len(depth_raw.shape) == 3:
                depth_raw = depth_raw[:, :, 0]

            depth_colored = depth_to_colormap(depth_raw)

        # Resize depth to match RGB if needed
        if depth_colored.shape[:2] != frame_rgb.shape[:2]:
            depth_colored = cv2.resize(depth_colored, (frame_rgb.shape[1], frame_rgb.shape[0]))

        # Combine side-by-side
        combined = np.hstack([frame_rgb, depth_colored])

        # Add labels
        cv2.putText(combined, "RGB", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(combined, "Depth", (frame_rgb.shape[1] + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        with lock:
            output_frame = combined.copy()


def generate_frames():
    """Generator that yields MJPEG frames"""
    global output_frame

    while True:
        with lock:
            if output_frame is None:
                continue
            frame = output_frame.copy()

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        time.sleep(0.033)  # ~30 fps


@app.route('/')
def index():
    """Simple HTML page with video stream"""
    return '''
    <html>
    <head>
        <title>RealSense D415 Stream</title>
    </head>
    <body>
        <h1>RealSense D415 - RGB + Depth</h1>
        <img src="/video_feed">
        <p>Depth colormap: Blue=near, Red=far (0.2m - 5m range)</p>
    </body>
    </html>
    '''


@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    # Start camera thread
    t = threading.Thread(target=camera_thread, daemon=True)
    t.start()

    # Wait for first frame
    time.sleep(2)

    print("Starting RealSense stream server on port 8080...")
    print("Forward port 8080 in VS Code, then open http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, threaded=True)
