"""Shadow collector: read-only 1Hz nvidia-smi + scheme query. NEVER writes (dry-run always).

optimize (P4 r27):
 - nvidia-smi left PATH after the 617.14 driver refresh; find_nvidia_smi() falls back
   to the DriverStore copy so续採 cannot silently append empty rows.
 - perf labels: --fps-file + --fps-process ingest a concurrently running PresentMon CSV.
   PresentMon's --date_time carries a constant clock offset on this box, so the series
   is rebased onto capture start when it disagrees with wall clock by >120s (offset
   printed). The file is re-read every --fps-reload seconds so labels exist while the
   capture runs; rows are merged by timestamp (no duplicates).
 - fps/p95 stay empty = honest missing when no PresentMon file is supplied.
"""
import argparse
import csv
import glob
import shutil
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

NVSMI_HINTS = [
    r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    r"C:\Windows\System32\nvidia-smi.exe",
]
_NVSMI = ""


def find_nvidia_smi():
    global _NVSMI
    if _NVSMI:
        return _NVSMI
    exe = shutil.which("nvidia-smi")
    if exe:
        _NVSMI = exe
        return exe
    for h in NVSMI_HINTS:
        if Path(h).exists():
            _NVSMI = h
            return h
    hits = glob.glob(r"C:\Windows\System32\DriverStore\FileRepository\nv*\nvidia-smi.exe")
    _NVSMI = sorted(hits)[-1] if hits else ""
    return _NVSMI


def snap_gpu():
    exe = find_nvidia_smi()
    if not exe:
        return ["", "", "", "", ""]
    try:
        r = subprocess.run(
            [exe, "--query-gpu=utilization.gpu,clocks.sm,power.draw,temperature.gpu,power.limit",
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


def _parse_time(cell):
    """(value, kind) from a PresentMon time cell; kind 'numeric' | 'epoch' | ''."""
    raw = str(cell).strip()
    try:
        return float(raw), "numeric"
    except (TypeError, ValueError):
        pass
    probe = raw[:26] if len(raw) > 26 else raw   # trim 7-digit fractional seconds
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(probe, fmt).timestamp(), "epoch"
        except ValueError:
            continue
    return 0.0, ""


def load_presentmon(path, wall0, process="", rebase_floor=120.0):
    """PresentMon CSV -> ([(epoch_seconds, frame_ms)], note).

    Columns accepted: MsBetweenPresents / FrameTime (ms) with CPUStartDateTime /
    CPU Start Time / CPUStartTime / TimeInSeconds. process filters the Application
    column (case-insensitive) so桌面合成 (dwm.exe) frames never enter a game cell.
    """
    rows = []
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            rd = csv.DictReader(f)
            norm = {(c or "").strip().lower(): c for c in (rd.fieldnames or [])}
            ft = (norm.get("msbetweenpresents") or norm.get("frametime (ms)")
                  or norm.get("frametime") or norm.get("msbetweendisplaychange"))
            tc = (norm.get("cpu start time") or norm.get("cpustartdatetime")
                  or norm.get("cpustarttime") or norm.get("timeinseconds")
                  or norm.get("time in seconds") or norm.get("cpu start time (ns)"))
            ac = norm.get("application") or norm.get("processname")
            if not ft or not tc:
                return [], f"columns not matched (frame={ft}, time={tc})"
            want = process.strip().lower()
            raw = []
            numeric = False
            for r in rd:
                if want and ac and (r.get(ac, "") or "").strip().lower() != want:
                    continue
                t, kind = _parse_time(r.get(tc, ""))
                if not kind:
                    continue
                try:
                    raw.append((t, float(r[ft])))
                except (TypeError, ValueError):
                    continue
                numeric = numeric or (kind == "numeric")
    except OSError as e:
        return [], f"open failed: {e}"
    if not raw:
        return [], "no frame rows"
    tmax = max(t for t, _ in raw)
    note = ""
    if numeric and tmax > 1e12:
        raw = [(t / 1e9, v) for t, v in raw]
        note = "ns rebased"
    elif numeric and tmax > 1e9:
        raw = [(t / 1e3, v) for t, v in raw]
        note = "ms rebased"
    tmin = min(t for t, _ in raw)
    tmax = max(t for t, _ in raw)
    if numeric or abs(tmax - wall0) > rebase_floor:
        off = wall0 - tmin
        rows = [(t + off, v) for t, v in raw]
        return rows, (note + f"; rebased onto capture start ({off:+.1f}s)").lstrip("; ")
    return raw, "wall-clock aligned"


def merge_series(dst, src):
    merged = dict(dst)
    for t, v in src:
        merged[t] = v
    return merged


def fps_window(series, wall_epoch, back=1.5, fwd=0.5):
    """(fps, p95_ms) over frames inside [wall-back, wall+fwd]; ('','') when empty."""
    win = [v for t, v in series if wall_epoch - back <= t <= wall_epoch + fwd]
    if not win:
        return "", ""
    fps = len(win) / (back + fwd)
    s = sorted(win)
    idx = min(len(s) - 1, int(round(0.95 * (len(s) - 1))))
    return f"{fps:.1f}", f"{s[idx]:.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--work", default="W0")
    ap.add_argument("--acdc", default="AC")
    ap.add_argument("--gear", default="Balance-readonly")
    ap.add_argument("--out", default="",
                    help="override output file (must use *_part*.csv naming)")
    ap.add_argument("--fps-file", default="",
                    help="PresentMon CSV (run PresentMon concurrently over the same window)")
    ap.add_argument("--fps-process", default="",
                    help="Application column filter, e.g. game.exe (excludes dwm.exe desktop frames)")
    ap.add_argument("--fps-reload", type=float, default=30.0,
                    help="re-read the PresentMon CSV every N seconds while capturing")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT
    wall0 = time.time()
    series = {}
    note = "no --fps-file"
    if args.fps_file:
        rows, note = load_presentmon(args.fps_file, wall0, args.fps_process)
        series = merge_series(series, rows)
    new = not out_path.exists()
    print(f"nvidia-smi: {find_nvidia_smi() or 'NOT FOUND'}; fps frames: {len(series)} ({note})")
    last_reload = time.time()
    with out_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        t0 = time.time()
        n = 0
        while time.time() - t0 < args.seconds:
            now = datetime.now()
            if args.fps_file and time.time() - last_reload >= args.fps_reload:
                rows, note = load_presentmon(args.fps_file, wall0, args.fps_process)
                before = len(series)
                series = merge_series(series, rows)
                last_reload = time.time()
                if len(series) != before:
                    print(f"  fps reload: +{len(series) - before} frames ({note})")
            g = snap_gpu()
            fps, p95 = fps_window(series, now.timestamp()) if series else ("", "")
            w.writerow([now.isoformat(timespec="milliseconds"),
                        args.work, args.acdc, args.gear] + g + [fps, p95]
                       + ["stub-1", "1.0", "1.0"])
            f.flush()
            n += 1
            time.sleep(1.0)
    print(f"shadow appended {n} rows -> {out_path} (read-only, zero writes)")


if __name__ == "__main__":
    main()
