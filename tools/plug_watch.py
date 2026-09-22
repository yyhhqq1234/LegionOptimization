"""Plug-event watcher: polls Win32_Battery (read-only), logs changes. No writes to system."""
import argparse
import csv
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "datasets" / "plug_events.csv"


def snap():
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Battery | Select-Object -ExpandProperty BatteryStatus"],
        capture_output=True, text=True, timeout=15)
    st = r.stdout.strip().split()[0] if r.stdout.strip() else ""
    r2 = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Battery | Select-Object -ExpandProperty EstimatedChargeRemaining"],
        capture_output=True, text=True, timeout=15)
    ch = r2.stdout.strip().split()[0] if r2.stdout.strip() else ""
    return st, ch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--interval", type=int, default=5)
    args = ap.parse_args()
    new = not OUT.exists()
    with OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "event", "battery_status", "charge_pct"])
        prev = snap()
        w.writerow([datetime.now().isoformat(timespec="milliseconds"),
                    "watch-start", prev[0], prev[1]])
        t0 = time.time()
        n = 0
        while time.time() - t0 < args.seconds:
            time.sleep(args.interval)
            cur = snap()
            if cur != prev:
                w.writerow([datetime.now().isoformat(timespec="milliseconds"),
                            "power-change", cur[0], cur[1]])
                f.flush()
                n += 1
                prev = cur
    print(f"plug watch done, changes={n} -> {OUT} (read-only, zero writes)")


if __name__ == "__main__":
    main()
