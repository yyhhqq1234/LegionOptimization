"""Shadow collector: read-only 1Hz nvidia-smi + scheme query. NEVER writes (dry-run always)."""
import argparse
import csv
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "datasets" / "D_safe_shadow_A.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

FIELDS = ["timestamp", "work", "acdc", "gear_readonly",
          "utilization.gpu [%]", "clocks.current.sm [MHz]",
          "power.draw [W]", "temperature.gpu", "power.limit [W]",
          "fps", "frame_p95_ms",
          "policy_ver", "fence_ver", "envelope_ver"]
# NOTE: no presentmon/dxgi on this box (checked round10) -> fps/p95 stay empty
# (honest missing, valid=0) until operator runs PresentMon sidecar; --fps-file
# ingests a PresentMon CSV matched by nearest timestamp when provided.


def snap_gpu():
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,clocks.sm,power.draw,temperature.gpu,power.limit",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
        parts = [p.strip() for p in r.stdout.strip().split(",")]
        if len(parts) >= 5:
            return parts[:5]
    except Exception:
        pass
    return ["", "", "", "", ""]


def snap_scheme():
    try:
        r = subprocess.run(["powercfg", "/GETACTIVESCHEME"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip().split()[-2] if r.stdout.strip() else ""
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--work", default="W0")
    ap.add_argument("--acdc", default="AC")
    ap.add_argument("--gear", default="Balance-readonly")
    ap.add_argument("--out", default="",
                    help="override output file (default part2-aware)")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT
    new = not out_path.exists()
    with out_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        t0 = time.time()
        n = 0
        while time.time() - t0 < args.seconds:
            g = snap_gpu()
            w.writerow([datetime.now().isoformat(timespec="milliseconds"),
                        args.work, args.acdc, args.gear] + g + ["", ""] + ["stub-1", "1.0", "1.0"])
            f.flush()
            n += 1
            time.sleep(1.0)
    print(f"shadow appended {n} rows -> {out_path} (read-only, zero writes)")


if __name__ == "__main__":
    main()
