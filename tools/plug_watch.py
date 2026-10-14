"""Plug-event watcher: polls Win32_Battery (read-only), logs PLUG/UNPLUG transitions.

Win32_Battery.BatteryStatus: 1 = discharging (running on battery), 2 = AC power/charging.
Only a status transition counts as a plug event. Battery-percent drift is logged separately
as charge-change, because the r33-era watcher wrote it as "power-change" and the E4 report
counted every non-watch-start row as a plug event -- i.e. a 1% battery drop could satisfy
"at least one plug event" (r34 fix; that would have been a fabricated pass).
"""
import argparse
import csv
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "datasets" / "plug_events.csv"

STATUS_AC = "2"           # AC power / charging
STATUS_DC = "1"           # discharging (on battery)


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


def event_for(status):
    """Status transition -> event name ('plug-in' when AC appears, 'unplug' when it is lost)."""
    if status == STATUS_AC:
        return "plug-in"
    if status == STATUS_DC:
        return "unplug"
    return f"status:{status}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--interval", type=int, default=5)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    out = Path(args.out) if args.out else OUT
    new = not out.exists()
    with out.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "event", "battery_status", "charge_pct"])
        prev_status, prev_charge = snap()
        w.writerow([datetime.now().isoformat(timespec="milliseconds"),
                    "watch-start", prev_status, prev_charge])
        f.flush()
        print(f"plug watch: start status={prev_status} charge={prev_charge} "
              f"(1=DC discharging, 2=AC charging)")
        t0 = time.time()
        plugs = 0
        while time.time() - t0 < args.seconds:
            time.sleep(args.interval)
            status, charge = snap()
            ts = datetime.now().isoformat(timespec="milliseconds")
            if status != prev_status:
                ev = event_for(status)
                w.writerow([ts, ev, status, charge])
                f.flush()
                plugs += 1
                print(f"  {ev} @ {ts} (status {prev_status} -> {status}, charge {charge})")
                prev_status = status
            elif charge != prev_charge:
                w.writerow([ts, "charge-change", status, charge])
                f.flush()
            prev_charge = charge
    print(f"plug watch done, plug transitions={plugs} -> {out} (read-only, zero writes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
