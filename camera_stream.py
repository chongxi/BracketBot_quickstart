#!/usr/bin/env python3
"""Flask app to stream USB camera video over HTTP

Usage:
    python camera_stream.py [device]

Examples:
    python camera_stream.py        # Use default /dev/video0
    python camera_stream.py 4      # Use /dev/video4 (RealSense RGB)
"""

import cv2
from flask import Flask, Response
import threading
import time
import sys

app = Flask(__name__)

# Parse device argument
device = int(sys.argv[1]) if len(sys.argv) > 1 else 0

# Global variables for thread-safe camera access
output_frame = None
lock = threading.Lock()


def camera_thread():
    """Continuously capture frames in a separate thread"""
    global output_frame

    print(f"Opening /dev/video{device}...")
    cap = cv2.VideoCapture(device)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 60)
    cap.set(cv2.CAP_PROP_AUTO_WB, 1)
    cap.set(cv2.CAP_PROP_WB_TEMPERATURE, 4500)

    print(f"Actual FPS: {cap.get(cv2.CAP_PROP_FPS)}")

    print(f"Camera opened: {cap.isOpened()}")

    # Warm up
    time.sleep(1)
    for _ in range(5):
        cap.read()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        with lock:
            output_frame = frame.copy()


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

        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        time.sleep(0.016)  # ~60 fps


@app.route('/')
def index():
    """Simple HTML page with video stream"""
    return '''
    <html>
    <head>
        <title>Camera Stream</title>
    </head>
    <body>
        <h1>USB Camera Stream</h1>
        <img src="/video_feed" width="640" height="480">
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

    print("Starting camera stream server...")
    print("Access the stream at http://192.168.22.175:8080")
    print("Or try: http://10.42.0.1:8080")
    app.run(host='0.0.0.0', port=8080, threaded=True)
