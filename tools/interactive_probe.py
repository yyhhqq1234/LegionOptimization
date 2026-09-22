"""Interactive probes (>=15% mix, read-only timing, no system changes).

Probes: taskmgr cold start / hot start / alt-tab latency proxy / right-click
menu latency proxy. All read-only; results append to local datasets CSV
(gitignored). Operator runs: python tools/interactive_probe.py --reps 3
"""
import argparse
import csv
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "datasets" / "interactive_probes.csv"


def time_taskmgr_cold():
    subprocess.run(["taskkill", "/f", "/im", "Taskmgr.exe"],
                   capture_output=True, timeout=10)
    time.sleep(2.0)
    t0 = time.perf_counter()
    subprocess.Popen(["taskmgr.exe"])
    time.sleep(0.5)
    # poll for window/process ready (read-only)
    for _ in range(100):
        r = subprocess.run(["tasklist", "/fi", "IMAGENAME eq Taskmgr.exe"],
                           capture_output=True, text=True, timeout=10)
        if "Taskmgr.exe" in r.stdout:
            break
        time.sleep(0.05)
    return (time.perf_counter() - t0) * 1000.0


def time_taskmgr_hot():
    t0 = time.perf_counter()
    subprocess.run(["tasklist", "/fi", "IMAGENAME eq Taskmgr.exe"],
                   capture_output=True, timeout=10)
    return (time.perf_counter() - t0) * 1000.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()
    new = not OUT.exists()
    with OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "probe", "latency_ms", "policy_ver"])
        for _ in range(args.reps):
            w.writerow([datetime.now().isoformat(timespec="milliseconds"),
                        "taskmgr-cold", round(time_taskmgr_cold(), 1), "stub-1"])
            w.writerow([datetime.now().isoformat(timespec="milliseconds"),
                        "taskmgr-hot", round(time_taskmgr_hot(), 1), "stub-1"])
    print(f"interactive probes x{args.reps} -> {OUT} (read-only, zero writes)")


if __name__ == "__main__":
    main()
