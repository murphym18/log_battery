#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import csv
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path.home() / ".local" / "share" / "battery-logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Choose one: "boot-id", "boot-number", or "boot-time"
FILENAME_SCHEME = os.environ.get("BATLOG_FILENAME_SCHEME", "boot-id")

def read_first_battery():
    p = Path("/sys/class/power_supply")
    bats = sorted([d.name for d in p.iterdir() if d.is_dir() and d.name.startswith("BAT")])
    if not bats:
        raise RuntimeError("No /sys/class/power_supply/BAT* device found")
    return bats[0]

def read_sys(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def get_boot_id():
    return read_sys("/proc/sys/kernel/random/boot_id")  # UUID

def get_boot_time_iso():
    # Current time minus uptime -> boot time
    now = time.time()
    with open("/proc/uptime", "r") as f:
        up = float(f.read().split()[0])
    boot_ts = datetime.fromtimestamp(now - up, tz=timezone.utc)
    return boot_ts.strftime("%Y%m%dT%H%M%SZ")

def get_boot_number_from_journal():
    """
    Returns a 1-based boot count where the *current* boot is the total number
    of boots listed by `journalctl --list-boots`. Caveat: rotates with journal.
    """
    try:
        out = subprocess.check_output(["journalctl", "--list-boots"], text=True)
    except Exception:
        return None
    # Lines look like: "  0 3f2b2f4e9d3... Fri 2025-08-22 ... — Fri 2025-08-22 ..."
    lines = [ln for ln in out.splitlines() if ln.strip()]
    # Count boots; current boot index “0” exists → current boot number = len(lines)
    return len(lines) if lines else None

def make_outfile_name(scheme):
    if scheme == "boot-id":
        bid = get_boot_id()
        return LOG_DIR / f"battery_{bid}.csv"
    elif scheme == "boot-number":
        n = get_boot_number_from_journal()
        if n is None:
            # Fallback to boot time
            bt = get_boot_time_iso()
            return LOG_DIR / f"battery_{bt}.csv"
        return LOG_DIR / f"battery_boot{n:05d}.csv"
    elif scheme == "boot-time":
        bt = get_boot_time_iso()
        return LOG_DIR / f"battery_{bt}.csv"
    else:
        # Unknown scheme → default to boot-id
        bid = get_boot_id()
        return LOG_DIR / f"battery_{bid}.csv"

def read_battery_sample(bat_name):
    base = Path("/sys/class/power_supply") / bat_name
    percent = read_sys(base / "capacity")
    state = read_sys(base / "status")  # Charging/Discharging/Full
    # Different laptops expose either energy_* (Wh) or charge_* (mAh)
    energy_full = read_sys(base / "energy_full") or read_sys(base / "charge_full")
    energy_now  = read_sys(base / "energy_now")  or read_sys(base / "charge_now")
    voltage_now = read_sys(base / "voltage_now")  # µV (often)
    power_now   = read_sys(base / "power_now") or read_sys(base / "current_now")
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "percent": percent,
        "state": state,
        "energy_full": energy_full,
        "energy_now": energy_now,
        "voltage_now": voltage_now,
        "power_now": power_now,
    }

def main():
    bat = read_first_battery()
    outfile = make_outfile_name(FILENAME_SCHEME)

    new_file = not outfile.exists()
    with open(outfile, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp","percent","state","energy_full","energy_now","voltage_now","power_now","battery","scheme"]
        )
        if new_file:
            writer.writeheader()

        print(f"Logging to: {outfile}")
        print(f"Battery: {bat}  | filename scheme: {FILENAME_SCHEME}")
        print("Unplug the charger for your idle test. Press Ctrl+C to stop early.\n")

        try:
            while True:
                row = read_battery_sample(bat)
                row["battery"] = bat
                row["scheme"] = FILENAME_SCHEME
                writer.writerow(row)
                f.flush()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopped by user.")
        # No special handling for power-off; the file will contain samples up to the last minute.

if __name__ == "__main__":
    # Optional: allow `--scheme boot-id|boot-number|boot-time`
    if len(sys.argv) > 1 and sys.argv[1] == "--scheme" and len(sys.argv) > 2:
        os.environ["BATLOG_FILENAME_SCHEME"] = sys.argv[2]
    main()

