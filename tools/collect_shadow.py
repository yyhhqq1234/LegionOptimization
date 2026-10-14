"""Shadow collector: read-only 1Hz nvidia-smi + scheme query. NEVER writes (dry-run always).

optimize (P4 r27): nvidia-smi left PATH after the 617.14 driver refresh -> find_nvidia_smi()
 falls back to the DriverStore copy. Perf labels come from a concurrently recorded PresentMon
 CSV joined afterwards (tools/fps_join.py / tools/run_shadow_window.py).

optimize (P4 r29): --sense-gear reads the REAL gear from LENOVO_GAMEZONE_DATA.GetThermalMode
 instead of trusting the command-line label.

optimize (P4 r36): the Windows power scheme is a real independent variable, so the CSV carries
 a trailing `scheme` column; a schema guard refuses to append to a file whose header differs.

optimize (P4 r42): W3/W4/W7-style workloads are CPU-bound and look exactly like idle through
 nvidia-smi alone (measured on the W3 rebuild: GPU 0 percent / 4.36W / 51C while 2 dotnet
 processes were compiling). CPU utilization is available WITHOUT a driver through the WMI
 performance counter, so the CSV now carries `cpu_util` too. `cpu_temp_c` still has no channel
 pre-E5 and is not fabricated anywhere.
"""
import argparse
import csv
import glob
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "artifacts" / "datasets" / "D_safe_shadow_A.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

try:
    import sense.lenovo_wmi as lw
except Exception:                      # keep the collector usable without the module
    lw = None

FIELDS = ["timestamp", "work", "acdc", "gear_readonly",
          "utilization.gpu [%]", "clocks.current.sm [MHz]",
          "power.draw [W]", "temperature.gpu", "power.limit [W]",
          "fps", "frame_p95_ms",
          "policy_ver", "fence_ver", "envelope_ver",
          "scheme", "cpu_util"]

NVSMI_HINTS = [
    r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    r"C:\Windows\System32\nvidia-smi.exe",
]
_NVSMI = ""
_CPU_PS = ("(Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor "
           "-Filter \"Name='_Total'\").PercentProcessorTime")


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
    """Active power scheme name (e.g. 节能 / 高性能) - a real environment variable."""
    try:
        r = subprocess.run(["powercfg", "/GETACTIVESCHEME"], capture_output=True,
                           text=True, timeout=10)
        out = r.stdout.strip()
        if not out:
            return ""
        return out.split("(", 1)[1].rstrip(")") if "(" in out else out
    except Exception:
        return ""


def snap_cpu_util():
    """CPU total utilization (percent) via the WMI perf counter - no driver required."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _CPU_PS],
                           capture_output=True, text=True, timeout=15)
        s = (r.stdout or "").strip()
        return s if s.isdigit() else ""
    except Exception:
        return ""


def real_gear(fallback_label):
    """Real gear from the Lenovo WMI module; falls back to the label (marked) if absent."""
    if lw is None:
        return fallback_label
    try:
        name, mode = lw.read_gear()
    except Exception:
        name, mode = None, None
    if name:
        return name
    if mode is not None:
        return f"mode:{mode}"
    return fallback_label


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


def _app_match(app, want):
    """Application-column match: exact, with .exe, or stem-equal.

    PresentMon's Application column carries the file name (e.g. "ff7rebirth_.exe"), so a
    --process value without the extension would match nothing and the whole window would
    come back with zero frame labels (r37: a 2h game window was lost that way and had to be
    re-joined). Accepting the stem form keeps the CLI forgiving without loosening the filter.
    """
    if not want:
        return True
    a = (app or "").strip().lower()
    w = want.strip().lower()
    if a == w or a == w + ".exe":
        return True
    return a.rsplit(".", 1)[0] == w


def load_presentmon(path, wall0, process="", rebase_floor=120.0):
    """PresentMon CSV -> ([(epoch_seconds, frame_ms)], note).

    Columns accepted: MsBetweenPresents / FrameTime (ms) with CPUStartDateTime /
    CPU Start Time / CPUStartTime / TimeInSeconds. process filters the Application
    column (case-insensitive) so desktop composition (dwm.exe) frames never enter a
    game cell.
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
                if ac and want and not _app_match(r.get(ac, ""), want):
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
    ap.add_argument("--gear", default="Balance-readonly",
                    help="label used only when --sense-gear is off or the read fails")
    ap.add_argument("--sense-gear", action="store_true",
                    help="write the REAL gear from Lenovo ACPI-WMI (r29) instead of the label")
    ap.add_argument("--no-scheme", action="store_true",
                    help="skip the trailing power-scheme column read (default: read it)")
    ap.add_argument("--no-cpu", action="store_true",
                    help="skip the CPU-utilization column read (default: read it)")
    ap.add_argument("--out", default="",
                    help="override output file (must use *_part*.csv naming)")
    ap.add_argument("--fps-file", default="",
                    help="PresentMon CSV (run PresentMon concurrently over the same window)")
    ap.add_argument("--fps-process", default="",
                    help="Application column filter, e.g. game.exe (excludes dwm.exe frames)")
    ap.add_argument("--fps-reload", type=float, default=30.0,
                    help="re-read the PresentMon CSV every N seconds while capturing")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT
    new = not out_path.exists()
    if not new:
        # schema guard: appending to a file with a different header silently shifts columns
        # (the old "mixed-column CSV" failure). Refuse and ask for a new part file.
        try:
            with out_path.open(encoding="utf-8", errors="replace") as fh:
                head = fh.readline().strip()
        except OSError:
            head = ""
        if head and head.split(",") != FIELDS:
            print(f"ERROR: {out_path.name} header has {len(head.split(','))} columns, "
                  f"current schema has {len(FIELDS)} (added 'cpu_util' in r42). "
                  f"Write to a new --out file instead of appending.")
            return 2
    wall0 = time.time()
    series = {}
    note = "no --fps-file"
    if args.fps_file:
        rows, note = load_presentmon(args.fps_file, wall0, args.fps_process)
        series = merge_series(series, rows)
    print(f"nvidia-smi: {find_nvidia_smi() or 'NOT FOUND'}; fps frames: {len(series)} ({note}); "
          f"sense-gear={'on' if args.sense_gear else 'off'}; scheme={'off' if args.no_scheme else 'on'}; "
          f"cpu={'off' if args.no_cpu else 'on'}")
    last_reload = time.time()
    cache_scheme, cache_cpu = "", ""     # r43: slow variables cached to keep the 1Hz cadence
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
            gear = real_gear(args.gear) if args.sense_gear else args.gear
            # r43: scheme and cpu are slow variables. Polling them every tick added ~0.8s per
            # tick (600s produced only 335 rows, i.e. 0.56Hz instead of 1Hz). They are cached
            # now: scheme refreshes every 10th tick, cpu every 5th.
            if not args.no_scheme and (n % 10 == 0 or cache_scheme == ""):
                cache_scheme = snap_scheme()
            if not args.no_cpu and (n % 5 == 0 or cache_cpu == ""):
                cache_cpu = snap_cpu_util()
            scheme, cpu = cache_scheme, cache_cpu
            fps, p95 = fps_window([(t, v) for t, v in series.items()],
                                  now.timestamp()) if series else ("", "")
            w.writerow([now.isoformat(timespec="milliseconds"),
                        args.work, args.acdc, gear] + g + [fps, p95]
                       + ["stub-1", "1.0", "1.0", scheme, cpu])
            f.flush()
            n += 1
            time.sleep(1.0)
    print(f"shadow appended {n} rows -> {out_path} (read-only, zero writes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
