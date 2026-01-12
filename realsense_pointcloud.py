#!/usr/bin/env python3
"""RealSense D415 Point Cloud Visualization - WebSocket + Binary Transfer

Usage:
    pip install flask-sock
    python realsense_pointcloud.py

Open browser at http://localhost:8081 to view 3D point cloud.
Controls:
    - Mouse drag: Rotate view
    - Mouse wheel: Zoom
    - Right-click drag: Pan
"""

import numpy as np
import pyrealsense2 as rs
from flask import Flask, render_template_string
from flask_sock import Sock
import time

app = Flask(__name__)
sock = Sock(app)

# Settings
DOWNSAMPLE = 2
MAX_POINTS = 30000


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RealSense Point Cloud</title>
    <style>
        body { margin: 0; overflow: hidden; }
        #info {
            position: absolute; top: 10px; left: 10px;
            color: white; font-family: monospace;
            background: rgba(0,0,0,0.7); padding: 10px;
        }
    </style>
    <script type="importmap">
        {
            "imports": {
                "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
                "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
            }
        }
    </script>
</head>
<body>
    <div id="info">Connecting...</div>
    <script type="module">
        import * as THREE from 'three';
        import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

        let scene, camera, renderer, controls, points;
        let ws;
        let frameCount = 0;
        let lastTime = performance.now();
        let fps = 0;

        function init() {
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x111111);

            camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.01, 100);
            camera.position.set(0, 0.5, -0.5);

            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.body.appendChild(renderer.domElement);

            controls = new OrbitControls(camera, renderer.domElement);
            controls.target.set(0, 0, 1);
            controls.update();

            // Point cloud with pre-allocated buffers
            const geometry = new THREE.BufferGeometry();
            const material = new THREE.PointsMaterial({
                size: 0.008,
                vertexColors: true,
                sizeAttenuation: true
            });
            points = new THREE.Points(geometry, material);
            scene.add(points);

            // Axes helper
            const axesHelper = new THREE.AxesHelper(0.3);
            scene.add(axesHelper);

            window.addEventListener('resize', onWindowResize);
            animate();
            connectWebSocket();
        }

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            ws.binaryType = 'arraybuffer';

            ws.onopen = () => {
                document.getElementById('info').textContent = 'Connected, waiting for data...';
            };

            ws.onmessage = (event) => {
                const data = event.data;
                if (data instanceof ArrayBuffer) {
                    updatePointCloud(data);
                }
            };

            ws.onclose = () => {
                document.getElementById('info').textContent = 'Disconnected. Reconnecting...';
                setTimeout(connectWebSocket, 1000);
            };

            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                ws.close();
            };
        }

        function updatePointCloud(buffer) {
            const view = new DataView(buffer);
            const numPoints = view.getUint32(0, true);

            if (numPoints === 0) return;

            // Binary format: [numPoints(4 bytes)][positions(numPoints*3*4 bytes)][colors(numPoints*3 bytes)]
            const posOffset = 4;
            const colorOffset = posOffset + numPoints * 3 * 4;

            const positions = new Float32Array(numPoints * 3);
            const colors = new Float32Array(numPoints * 3);

            // Read positions
            for (let i = 0; i < numPoints * 3; i++) {
                positions[i] = view.getFloat32(posOffset + i * 4, true);
            }

            // Flip Y axis and read colors
            for (let i = 0; i < numPoints; i++) {
                positions[i * 3 + 1] = -positions[i * 3 + 1]; // Flip Y

                colors[i * 3] = view.getUint8(colorOffset + i * 3) / 255;
                colors[i * 3 + 1] = view.getUint8(colorOffset + i * 3 + 1) / 255;
                colors[i * 3 + 2] = view.getUint8(colorOffset + i * 3 + 2) / 255;
            }

            points.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            points.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            points.geometry.computeBoundingSphere();

            // Calculate FPS
            frameCount++;
            const now = performance.now();
            if (now - lastTime >= 1000) {
                fps = frameCount;
                frameCount = 0;
                lastTime = now;
            }

            document.getElementById('info').innerHTML =
                `RealSense Point Cloud<br>${numPoints.toLocaleString()} points | ${fps} fps<br>` +
                `Drag: rotate | Scroll: zoom`;
        }

        function onWindowResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }

        init();
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@sock.route('/ws')
def websocket(ws):
    """WebSocket endpoint - streams point cloud data"""
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.color, 640, 480, rs.format.rgb8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    print("Starting RealSense pipeline for WebSocket client...")
    profile = pipeline.start(config)

    device = profile.get_device()
    print(f"Device: {device.get_info(rs.camera_info.name)}")

    pc = rs.pointcloud()
    align = rs.align(rs.stream.color)

    try:
        while True:
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)

            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()

            if not color_frame or not depth_frame:
                continue

            # Generate point cloud
            pc.map_to(color_frame)
            points = pc.calculate(depth_frame)

            # Get vertices and colors
            vertices = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)
            colors = np.asanyarray(color_frame.get_data()).reshape(-1, 3).astype(np.uint8)

            # Downsample
            vertices = vertices[::DOWNSAMPLE]
            colors = colors[::DOWNSAMPLE]

            # Filter zero points
            mask = ~(np.all(vertices == 0, axis=1))
            vertices = vertices[mask]
            colors = colors[mask]

            # Limit points
            if len(vertices) > MAX_POINTS:
                indices = np.random.choice(len(vertices), MAX_POINTS, replace=False)
                vertices = vertices[indices]
                colors = colors[indices]

            # Pack as binary: [num_points(uint32)][positions(float32*3*n)][colors(uint8*3*n)]
            num_points = len(vertices)
            binary_data = (
                np.array([num_points], dtype=np.uint32).tobytes() +
                vertices.astype(np.float32).tobytes() +
                colors.astype(np.uint8).tobytes()
            )

            ws.send(binary_data)

            time.sleep(0.033)  # ~30 fps

    except Exception as e:
        print(f"WebSocket closed: {e}")
    finally:
        pipeline.stop()
        print("Pipeline stopped")


if __name__ == '__main__':
    print("Starting point cloud server on port 8081...")
    print("Open http://localhost:8081 in your browser")
    app.run(host='0.0.0.0', port=8081, threaded=True)
