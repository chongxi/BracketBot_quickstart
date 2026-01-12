# USB Camera Streaming

Stream video from a USB camera on Raspberry Pi 5 to a web browser.

## Files

- `test_usb_camera.py` - Test camera capture and measure latency
- `camera_stream.py` - Flask server for live video streaming

## Setup

Install Flask if not already installed:
```bash
pip install flask
```

## Usage

### Test Camera

```bash
python3 test_usb_camera.py
```

This captures 3 test images to the `img/` folder and displays latency measurements.

### Stream Video

```bash
python3 camera_stream.py
```

The server runs on port 8080.

**Accessing the stream via VS Code Remote SSH:**

1. In VS Code, open Command Palette (Cmd+Shift+P)
2. Select "Forward a Port"
3. Enter `8080`
4. Open http://localhost:8080 in your browser

**Accessing directly (if on same network):**

Open http://<pi-ip>:8080 in your browser.

## Camera Settings

Both scripts configure:
- Buffer size: 1 (minimizes latency)
- Auto white balance: enabled
- White balance temperature: 4500K
