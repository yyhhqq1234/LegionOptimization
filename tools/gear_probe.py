"""Gear calibration probe: watch the Lenovo thermal mode while the operator walks Fn+Q.

Why: the gear value that the machine actually reports is only trustworthy once each
position has been labelled by the operator. This probe polls the read-only
GetThermalMode every second, records every change with a timestamp, and writes the
candidate mapping. Nothing is written to the machine; no Set* call is made.

Usage:
  python tools/gear_probe.py --seconds 180 --out artifacts/datasets/gear_probe.jsonl
  # press Fn+Q through all four positions while it runs, then:
  python tools/gear_probe.py --from-log artifacts/datasets/gear_probe.jsonl
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import sense.lenovo_wmi as lw   # noqa: E402

DEFAULT_OUT = ROOT / "artifacts" / "datasets" / "gear_probe.jsonl"


def watch(seconds, out_path, work=""):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"gear probe: polling GetThermalMode for {seconds}s -> {out_path.name}")
    print("  press Fn+Q through every gear position now (each change is logged with a timestamp)")
    t0 = time.time()
    last = None
    seen = []
    with out_path.open("a", encoding="utf-8") as f:
        while time.time() - t0 < seconds:
            mode = lw.read_thermal_mode()
            if mode is not None and mode != last:
                row = {"ts": datetime.now().isoformat(timespec="milliseconds"),
                       "thermal_mode": mode, "gear": lw.MODE_TO_GEAR.get(mode), "work": work}
                f.write(json.dumps(row, ensure_ascii=True) + "\n")
                f.flush()
                seen.append(mode)
                print(f"  mode change -> {mode} (gear={lw.MODE_TO_GEAR.get(mode) or 'unmapped'}) "
                      f"@ {row['ts']}")
                last = mode
            time.sleep(1.0)
    print(f"observed modes: {seen}")
    return seen


def summarise(log_path):
    seen = {}
    if not log_path.exists():
        print(f"no probe log at {log_path}")
        return {}
    with log_path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            seen.setdefault(r.get("thermal_mode"), []).append(r.get("ts"))
    print("mode -> first seen (count)")
    for mode, ts in sorted(seen.items(), key=lambda kv: (kv[0] is None, kv[0])):
        print(f"  {mode} -> {ts[0]} ({len(ts)} change rows)")
    print("map to fill: MODE_TO_GEAR in src/sense/lenovo_wmi.py "
          "(operator labels each position: Quiet / Balance / Beast / Extreme)")
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=180)
    ap.add_argument("--out", default="")
    ap.add_argument("--work", default="")
    ap.add_argument("--from-log", default="", help="summarise an existing probe log instead of polling")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else DEFAULT_OUT
    if args.from_log:
        summarise(Path(args.from_log))
        return 0
    watch(args.seconds, out_path, args.work)
    summarise(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
