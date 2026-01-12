#!/usr/bin/env python3
"""RealSense D415 Point Cloud Visualization - Web-based using Flask + Three.js

Usage:
    python realsense_pointcloud.py

Open browser at http://localhost:8081 to view 3D point cloud.
Controls:
    - Mouse drag: Rotate view
    - Mouse wheel: Zoom
    - Right-click drag: Pan
"""

import numpy as np
import pyrealsense2 as rs
from flask import Flask, Response, render_template_string
import threading
import json
import time

app = Flask(__name__)

# Global for point cloud data
pointcloud_data = None
lock = threading.Lock()

# Downsample factor (1 = full, 4 = 1/4 resolution for performance)
DOWNSAMPLE = 4


def camera_thread():
    """Capture frames and generate point cloud"""
    global pointcloud_data

    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.color, 640, 480, rs.format.rgb8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    print("Starting RealSense pipeline...")
    profile = pipeline.start(config)

    device = profile.get_device()
    print(f"Device: {device.get_info(rs.camera_info.name)}")

    pc = rs.pointcloud()
    align = rs.align(rs.stream.color)

    print("Generating point clouds...")

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
            colors = np.asanyarray(color_frame.get_data()).reshape(-1, 3)

            # Downsample for performance
            vertices = vertices[::DOWNSAMPLE]
            colors = colors[::DOWNSAMPLE]

            # Filter out zero points (no depth)
            mask = ~(np.all(vertices == 0, axis=1))
            vertices = vertices[mask]
            colors = colors[mask]

            # Further limit points for web performance
            max_points = 50000
            if len(vertices) > max_points:
                indices = np.random.choice(len(vertices), max_points, replace=False)
                vertices = vertices[indices]
                colors = colors[indices]

            with lock:
                pointcloud_data = {
                    'positions': vertices.tolist(),
                    'colors': colors.tolist()
                }

            time.sleep(0.1)  # ~10 fps for point cloud updates

    finally:
        pipeline.stop()


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
    <div id="info">Loading point cloud...</div>
    <script type="module">
        import * as THREE from 'three';
        import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

        let scene, camera, renderer, controls, points;

        function init() {
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x111111);

            camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.01, 100);
            // Position camera behind the origin, looking forward (+Z is depth direction)
            camera.position.set(0, 0.5, -0.5);

            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.body.appendChild(renderer.domElement);

            controls = new OrbitControls(camera, renderer.domElement);
            // Look at a point ~1m in front of camera
            controls.target.set(0, 0, 1);
            controls.update();

            // Initial empty point cloud
            const geometry = new THREE.BufferGeometry();
            const material = new THREE.PointsMaterial({
                size: 0.01,
                vertexColors: true,
                sizeAttenuation: true
            });
            points = new THREE.Points(geometry, material);
            scene.add(points);

            // Add axes helper (RGB = XYZ)
            const axesHelper = new THREE.AxesHelper(0.3);
            scene.add(axesHelper);

            // Add grid on XZ plane
            const gridHelper = new THREE.GridHelper(4, 20, 0x444444, 0x222222);
            gridHelper.rotation.x = Math.PI / 2; // Rotate to XY plane
            gridHelper.position.z = 2;
            scene.add(gridHelper);

            window.addEventListener('resize', onWindowResize);
            animate();
            fetchPointCloud();
        }

        function onWindowResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        function fetchPointCloud() {
            fetch('/pointcloud')
                .then(response => response.json())
                .then(data => {
                    if (data.positions && data.positions.length > 0) {
                        const numPoints = data.positions.length;
                        const positions = new Float32Array(numPoints * 3);
                        const colors = new Float32Array(numPoints * 3);

                        for (let i = 0; i < numPoints; i++) {
                            // RealSense: X right, Y down, Z forward
                            // Three.js: X right, Y up, Z toward viewer
                            // Transform: flip Y, keep X and Z
                            positions[i * 3] = data.positions[i][0];      // X
                            positions[i * 3 + 1] = -data.positions[i][1]; // Y (flip)
                            positions[i * 3 + 2] = data.positions[i][2];  // Z

                            colors[i * 3] = data.colors[i][0] / 255;
                            colors[i * 3 + 1] = data.colors[i][1] / 255;
                            colors[i * 3 + 2] = data.colors[i][2] / 255;
                        }

                        points.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
                        points.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
                        points.geometry.computeBoundingSphere();

                        document.getElementById('info').innerHTML =
                            `RealSense Point Cloud<br>${numPoints.toLocaleString()} points<br>` +
                            `Drag: rotate | Scroll: zoom | Right-drag: pan`;
                    }
                })
                .catch(err => {
                    console.error(err);
                    document.getElementById('info').textContent = 'Error loading point cloud';
                })
                .finally(() => setTimeout(fetchPointCloud, 100));
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


@app.route('/pointcloud')
def get_pointcloud():
    with lock:
        if pointcloud_data:
            return json.dumps(pointcloud_data)
        return json.dumps({'positions': [], 'colors': []})


if __name__ == '__main__':
    t = threading.Thread(target=camera_thread, daemon=True)
    t.start()

    time.sleep(2)

    print("Starting point cloud server on port 8081...")
    print("Open http://localhost:8081 in your browser")
    app.run(host='0.0.0.0', port=8081, threaded=True)
