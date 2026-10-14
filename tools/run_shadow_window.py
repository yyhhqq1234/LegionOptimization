"""One-command shadow window: PresentMon capture + shadow_run + fps backfill + E4 report.

Why: PresentMon holds its CSV exclusively while recording (Errno 13), so the label join can
only happen after the capture stops. Doing that by hand is three commands and two windows;
this script runs the whole window and leaves the joined JSONL plus the E4 report behind.

Shape (everything read-only; live actuation still has no path):
  1. start PresentMon (--timed <seconds+20> --date_time --session_name shadow<ts>)
  2. wait 3s, run tools/shadow_run.py for <seconds> (telemetry + policy + fence + BlackBox)
  3. wait for PresentMon to stop
  4. backfill fps/p95 into a NEW <name>.joined.jsonl (the raw JSONL is left untouched)
  5. run tools/e4_shadow_report.py over the joined file

Usage:
  python tools/run_shadow_window.py --seconds 600 --work W2 --process game.exe
  python tools/run_shadow_window.py --seconds 600 --work W2 --process game.exe --report
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from collect_shadow import fps_window, load_presentmon  # noqa: E402

PM_EXE = ROOT / "tools" / "presentmon" / "PresentMon-2.6.0-x64.exe"


def to_epoch(text):
    probe = (text or "").strip()
    probe = probe[:26] if len(probe) > 26 else probe
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(probe, fmt).timestamp()
        except ValueError:
            continue
    return None


def backfill(jsonl_in, pm_csv, process, out_path, back=1.5, fwd=0.5):
    rows = []
    with jsonl_in.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if not rows:
        return 0, "empty jsonl", None
    t0 = to_epoch(rows[0].get("ts", ""))
    if t0 is None:
        return 0, "unparsable first timestamp", None
    series, note = load_presentmon(str(pm_csv), t0, process)
    if not series:
        return 0, note, None
    series.sort()
    filled = 0
    for r in rows:
        t = to_epoch(r.get("ts", ""))
        if t is None:
            continue
        fps, p95 = fps_window(series, t, back, fwd)
        if fps:
            r["frames"] = {"fps": float(fps), "p95_ms": float(p95), "note": note}
            filled += 1
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")
    return filled, note, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=600, help="shadow window length")
    ap.add_argument("--work", default="W2")
    ap.add_argument("--acdc-label", default="", help="empty = read the real AC/DC state")
    ap.add_argument("--process", default="", help="target Application column, e.g. game.exe")
    ap.add_argument("--out-dir", default="artifacts/samples")
    ap.add_argument("--report", action="store_true", help="run tools/e4_shadow_report.py afterwards")
    args = ap.parse_args()

    if not PM_EXE.exists():
        print(f"PresentMon missing at {PM_EXE} (see tools/presentmon/README.md); "
              f"continuing without frame labels")
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pm_csv = out_dir / f"pm_{args.work}_{ts}.csv"
    jsonl = out_dir / f"e4_shadow_{args.work}_{ts}.jsonl"
    joined = out_dir / f"e4_shadow_{args.work}_{ts}.joined.jsonl"

    pm = None
    if PM_EXE.exists():
        sess = f"shadow{ts}"
        # NOTE: --process_name is deliberately NOT passed to PresentMon. Game exe names on
        # this box are non-standard (e.g. "ff7rebirth_.exe"): a wrong pattern yields zero
        # frames for the whole window. Capturing every process and filtering the Application
        # column during the join is the robust order (the CSV costs more disk, which is fine
        # because pm_*.csv is gitignored).
        cmd = [str(PM_EXE), "--timed", str(args.seconds + 20), "--session_name", sess,
               "--output_file", str(pm_csv), "--date_time", "--terminate_after_timed",
               "--no_console_stats"]
        pm = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"PresentMon recording -> {pm_csv.name} (session {sess}, all processes; "
              f"join filters Application={args.process or 'ALL'})")
        time.sleep(3)

    shadow_cmd = [sys.executable, str(ROOT / "tools" / "shadow_run.py"),
                  "--seconds", str(args.seconds), "--work", args.work, "--out", str(jsonl)]
    if args.acdc_label:
        shadow_cmd += ["--acdc-label", args.acdc_label]
    print("shadow_run: " + " ".join(shadow_cmd[1:]))
    rc = subprocess.call(shadow_cmd)
    if pm is not None:
        print("waiting for PresentMon to stop ...")
        try:
            pm.wait(timeout=60)
        except subprocess.TimeoutExpired:
            pm.terminate()
            pm.wait(timeout=30)
    if rc != 0:
        print(f"shadow_run exited {rc}")
        return rc

    if PM_EXE.exists() and pm_csv.exists():
        filled, note, total = backfill(jsonl, pm_csv, args.process, joined)
        print(f"fps backfill: {filled}/{total} rows labelled ({note}) -> {joined.name}")
    else:
        print("no PresentMon CSV; frame labels stay empty (honest missing)")

    if args.report:
        target = joined if joined.exists() else jsonl
        print(f"e4 report over {target.name}")
        return subprocess.call([sys.executable, str(ROOT / "tools" / "e4_shadow_report.py"),
                                "--glob", str(target.relative_to(ROOT)).replace("\\", "/"),
                                "--json-out", f"artifacts/samples/{target.stem}_report.json"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
