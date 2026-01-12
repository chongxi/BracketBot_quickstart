#!/usr/bin/env python3
"""Flask app to stream RealSense D415 RGB + Depth over HTTP using pyrealsense2

Usage:
    python realsense_stream.py
"""

import cv2
from flask import Flask, Response
import threading
import time
import numpy as np
import pyrealsense2 as rs

app = Flask(__name__)

# Global variables for thread-safe camera access
output_frame = None
lock = threading.Lock()

# Depth range in mm (D415 typical range)
DEPTH_MIN = 200    # 20cm
DEPTH_MAX = 5000   # 5m


def camera_thread():
    """Continuously capture frames using RealSense SDK"""
    global output_frame

    # Configure RealSense pipeline
    pipeline = rs.pipeline()
    config = rs.config()

    # Enable streams (both at 15fps to avoid sync issues)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    # Start pipeline
    print("Starting RealSense pipeline...")
    try:
        profile = pipeline.start(config)
    except Exception as e:
        print(f"Failed to start pipeline: {e}")
        return

    # Get device info
    device = profile.get_device()
    print(f"Device: {device.get_info(rs.camera_info.name)}")
    print(f"Serial: {device.get_info(rs.camera_info.serial_number)}")

    # Align depth to color camera viewpoint
    align = rs.align(rs.stream.color)

    # Create colorizer for depth visualization
    colorizer = rs.colorizer()
    colorizer.set_option(rs.option.color_scheme, 0)  # 0 = Jet colormap (blue=near, red=far)

    # Set depth range (D415 min reliable range is ~0.3m)
    colorizer.set_option(rs.option.min_distance, 0.3)  # 0.3m min
    colorizer.set_option(rs.option.max_distance, 4.0)  # 4m max

    print("Streaming started...")

    try:
        while True:
            # Wait for frames
            frames = pipeline.wait_for_frames()

            # Align depth to color viewpoint (reduces parallax artifacts)
            aligned_frames = align.process(frames)

            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()

            if not color_frame or not depth_frame:
                continue

            # Convert to numpy arrays
            frame_rgb = np.asanyarray(color_frame.get_data())

            # Colorize aligned depth
            depth_colorized = np.asanyarray(colorizer.colorize(depth_frame).get_data())

            # Combine side-by-side
            combined = np.hstack([frame_rgb, depth_colorized])

            # Add labels
            cv2.putText(combined, "RGB", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(combined, "Depth", (frame_rgb.shape[1] + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            with lock:
                output_frame = combined.copy()

    finally:
        pipeline.stop()


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
