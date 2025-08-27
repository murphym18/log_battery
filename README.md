# Battery Logger

A Python script for logging battery percentage and metrics during battery rundown tests.

## Overview

This tool logs battery data every minute to CSV files, designed for battery endurance testing. Each boot session creates a separate log file with detailed battery metrics.

## Installation

1. Install the systemd user service:
```bash
mkdir -p ~/.config/systemd/user
cp battery-logger.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable battery-logger
```

## Battery Rundown Test Procedure

1. **Preparation:**
   - Charge laptop to 100%
   - Shutdown completely
   - Unplug power adapter

2. **Start test:**
   - Power on laptop
   - Enable caffeine/disable sleep to keep screen on
   - The battery logger will start automatically via systemd
   - Leave laptop idle until it shuts down from low battery

3. **Results:**
   - Log files are saved to `~/.local/share/battery-logs/`
   - Each boot creates a unique CSV file with timestamp, battery %, and power metrics

## Manual Usage

Test the script manually:
```bash
python3 battery_log.py
```

Press Ctrl+C to stop.

## Configuration

Set filename scheme via environment variable:
```bash
export BATLOG_FILENAME_SCHEME=boot-time  # or boot-id, boot-number
python3 battery_log.py
```

Or use command line:
```bash
python3 battery_log.py --scheme boot-time
```

## Output Format

CSV files contain: timestamp, percent, state, energy_full, energy_now, voltage_now, power_now, battery, scheme