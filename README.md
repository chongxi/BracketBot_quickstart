# Bracket Bot Quickstart

For comprehensive documentation, visit our docs site: [https://docs.bracket.bot/docs/](https://docs.bracket.bot/docs/)

## Getting Started

To set up your robot, look at the setup folder:

[**Setup Guide**](./setup)

## Quick Setup Guide

### 1. Installation

#### Step 1: Clone the repository

```bash
cd ~
git clone https://github.com/chongxi/BracketBot_quickstart quickstart
cd quickstart
```

#### Step 2: Install system dependencies and GPIO lib

```bash
sudo apt update
sudo apt install -y swig python3-dev build-essential liblgpio-dev
```

#### Step 3: Run the OS setup script

This will set up the Python virtual environment, install all required packages, and configure system settings:

```bash
cd ~/quickstart/setup
bash setup_os.sh
```

The setup script will:
- Create a Python virtual environment at `~/quickstart/quickstart-venv`
- Install ODrive and other Python dependencies
- Configure system settings for optimal robot operation
- Set up serial port permissions

After the setup completes, activate the virtual environment:

```bash
cd ~/quickstart
source quickstart-venv/bin/activate
```

### 2. Motor Calibration

**Important:** Place the robot on a stand with wheels free to spin before calibration.

Run the motor calibration script:

```bash
python calibrate_motors.py
```

The calibration process will:
1. Connect to ODrive on `/dev/ttyAMA1`
2. Configure motor parameters (pole pairs, torque constant, current limits)
3. Configure encoder settings (Hall sensor mode, bandwidth)
4. Configure controller PID gains (velocity control)
5. Calibrate axis 0 (left motor) - you'll see the wheel spin slowly back and forth
6. Calibrate axis 1 (right motor) - same spinning motion
7. Save configuration and reboot the ODrive

**What you'll see during calibration:**
- Beeping sounds from the ODrive
- Slow back-and-forth spinning during motor calibration
- Smooth spinning during encoder offset calibration
- Brief velocity test (0.5 turns/sec)

After calibration completes, the ODrive will reboot. Wait 10-15 seconds before testing.

### 3. Test Motor Control (WASD Test)

Once calibration is complete and ODrive has rebooted, test the motors:

```bash
python test_wasd_stand.py
```

**Controls:**
- `W` - Both wheels forward
- `S` - Both wheels backward
- `A` - Left turn (differential steering)
- `D` - Right turn (differential steering)
- `Q` - Left wheel only forward
- `E` - Right wheel only forward
- `Z` - Left wheel only backward
- `C` - Right wheel only backward
- `SPACE` - Stop both wheels
- `+/-` - Increase/Decrease move speed
- `[/]` - Increase/Decrease turn speed
- `ESC` - Exit

**Note:** The test assumes the robot is on a stand with wheels free to spin. Default motor directions are:
- Axis 0 (left motor): reversed (negative values = forward)
- Axis 1 (right motor): normal (positive values = forward)

### Motor Configuration Details

The calibration sets up the following parameters:

**Motor Settings:**
- Pole pairs: 15
- Torque constant: 0.516875 (8.27/16)
- Calibration current: 5A
- Current range: 25A
- Current control bandwidth: 100 Hz

**Encoder Settings:**
- Mode: Hall sensor
- Counts per revolution: 90
- Bandwidth: 100 Hz
- Calibration scan distance: 150

**Controller Settings:**
- Control mode: Velocity control
- Velocity limit: 10 turns/sec
- Position gain: 1
- Velocity gain: 0.9302 (auto-calculated)
- Velocity integrator gain: 4.651 (auto-calculated)

## Troubleshooting

### Calibration Issues

**ODrive connection timeout:**
- Ensure ODrive is powered and connected to `/dev/ttyAMA1`
- Check voltage (should be around 20-24V)
- Verify serial connection is not in use by another process

**Motor vibration during test:**
- This was likely due to missing PID controller gains
- The current `calibrate_motors.py` includes proper `vel_gain` and `vel_integrator_gain` settings
- If vibration persists, check motor wiring and encoder connections

**Calibration fails with errors:**
- Check motor connections (all three phases)
- Verify Hall sensor connections
- Ensure wheels can spin freely
- Review error codes in the output

### WASD Test Issues

**Motors don't respond:**
- Wait 10-15 seconds after calibration for ODrive to fully reboot
- Check that motors entered closed loop control (script will show error if not)
- Verify no errors are present: check `axis0.error` and `axis1.error`

**Wrong motor directions:**
- The hardcoded directions in `test_wasd_stand.py` may not match your setup
- You can manually adjust the signs in the control commands
- Or run the full direction calibration from `setup/calibrate_drive.py`

## Next Steps

After successful motor testing:
1. Run the full setup process in the `setup/` folder for complete system configuration
2. Configure IMU and other sensors
3. Set up motor direction calibration for autonomous operation
4. Explore example scripts for more advanced control
