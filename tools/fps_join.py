"""Backfill PresentMon fps/p95 into a shadow part CSV.

Why offline: PresentMon holds its output CSV open exclusively while recording, so a
concurrent reader gets Permission denied. Capture shape is therefore
  PresentMon (same window) || collect_shadow (fps left empty)  ->  fps_join.py (after stop).
The join reuses the collector's own parser/window so both paths agree; the offset is
taken from the shadow's first row (capture start), or pass --offset to override.
Rows stay empty when no frames fall in the window = honest missing, never fabricated.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_shadow import fps_window, load_presentmon  # noqa: E402

TS_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f",
              "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")


def to_epoch(text):
    probe = (text or "").strip()
    probe = probe[:26] if len(probe) > 26 else probe
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(probe, fmt).timestamp()
        except ValueError:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shadow", required=True, help="shadow part CSV to label")
    ap.add_argument("--pm", required=True, help="PresentMon CSV (capture already stopped)")
    ap.add_argument("--process", default="", help="Application filter, e.g. game.exe")
    ap.add_argument("--offset", type=float, default=None,
                    help="seconds added to PresentMon timestamps (default: auto from first row)")
    ap.add_argument("--back", type=float, default=1.5)
    ap.add_argument("--fwd", type=float, default=0.5)
    ap.add_argument("--out", default="", help="default: rewrite --shadow in place (in place)")
    args = ap.parse_args()

    with open(args.shadow, newline="", encoding="utf-8-sig", errors="replace") as f:
        rd = csv.DictReader(f)
        fields = rd.fieldnames
        rows = list(rd)
    if not rows:
        print("shadow file has no rows")
        return 1
    t0 = to_epoch(rows[0].get("timestamp", ""))
    if t0 is None:
        print(f"unparsable shadow timestamp: {rows[0].get('timestamp')!r}")
        return 1

    series, note = load_presentmon(args.pm, t0, args.process)
    if not series:
        print(f"no PresentMon frames ({note})")
        return 1
    if args.offset is not None:
        series = [(t + args.offset, v) for t, v in series]
        note += f"; manual offset {args.offset:+.1f}s"
    series.sort()

    filled = 0
    for r in rows:
        t = to_epoch(r.get("timestamp", ""))
        if t is None:
            continue
        fps, p95 = fps_window(series, t, args.back, args.fwd)
        if fps:
            r["fps"], r["frame_p95_ms"] = fps, p95
            filled += 1

    out = args.out or args.shadow
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"backfilled {filled}/{len(rows)} rows ({note}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
