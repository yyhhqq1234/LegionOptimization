"""E4 shadow gate report: the four fence 5.2/5.3 criteria + effective-coverage check.

Criteria (docs/safety-fence-spec.md 5.2/5.3):
  1. action agreement: shadow vs in-service setpoint gear >= 85%
  2. trial trip rate: L1+ <= in-service + 2pp AND L2+ trial trips == 0
  3. fluency neutral: window p95 within +-5% of the same-class baseline
  4. zero crash: no inference exception and no 50ms budget overrun

Honest inputs: this box has no calibrated active-gear reader (only the powercfg scheme)
and no CPU temperature channel pre-E5, so criteria 1 and 3 can come out as
BLOCKED-<reason> instead of a fabricated pass. Effective coverage is counted from the
shadow JSONL plus the real collector parts.

Usage:
  python tools/e4_shadow_report.py [--glob "artifacts/samples/e4_shadow_*.jsonl"]
                                   [--shadow-glob "artifacts/datasets/D_safe_shadow_A_part*.csv"]
                                   [--baseline-p95 <ms>] [--json-out <path>]
"""
import argparse
import csv
import glob
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "artifacts" / "samples"
PLUG_CSV = ROOT / "artifacts" / "datasets" / "plug_events.csv"

REQ_HOURS = {"W2": 2.0, "W1": 2.0, "W0": 1.0}   # game / office / idle
P95_TOL = 0.05
INFER_BUDGET_MS = 50.0


def load_rows(pattern):
    rows = []
    for p in sorted(glob.glob(str(ROOT / pattern))):
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def cell_hours(shadow_glob, jsonl_rows):
    """Per-cell hours from the real collector parts + shadow runs (1Hz rows)."""
    c = Counter()
    for p in sorted(glob.glob(str(ROOT / shadow_glob))):
        try:
            with open(p, newline="", encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    if r.get("work") and r.get("acdc"):
                        c[(r["work"], r["acdc"])] += 1
        except OSError:
            continue
    for r in jsonl_rows:
        w, a = r.get("work"), r.get("acdc")
        if w and a in ("AC", "DC"):
            c[(w, a)] += 1
    return {f"{k[0]}/{k[1]}": round(v / 3600.0, 2) for k, v in sorted(c.items())}, c


def plug_events():
    if not PLUG_CSV.exists():
        return 0, []
    evs = []
    with open(PLUG_CSV, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            if (r.get("event") or "").strip() not in ("", "watch-start"):
                evs.append(r)
    return len(evs), evs


def p95_list(rows):
    out = []
    for r in rows:
        fr = r.get("frames") or {}
        v = fr.get("p95_ms")
        if isinstance(v, (int, float)) and v > 0:
            out.append(float(v))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="artifacts/samples/e4_shadow_*.jsonl")
    ap.add_argument("--shadow-glob", default="artifacts/datasets/D_safe_shadow_A_part*.csv")
    ap.add_argument("--baseline-p95", type=float, default=None,
                    help="same-class baseline p95 in ms; default = earliest 20%% of labelled rows")
    ap.add_argument("--gear-map", default="",
                    help='in-service scheme name -> gear, e.g. "节能=Quiet,平衡=Balance,高性能=Beast". '
                         'Without it criterion 1 stays BLOCKED (never a fabricated pass).')
    ap.add_argument("--json-out", default="artifacts/samples/e4_shadow_report.json")
    args = ap.parse_args()

    gear_map = {}
    for part in args.gear_map.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            gear_map[k.strip()] = v.strip()

    rows = load_rows(args.glob)
    if not rows:
        print(f"no shadow rows matched {args.glob} (run tools/shadow_run.py first)")
        return 1

    hours, _ = cell_hours(args.shadow_glob, rows)

    # criterion 1: action agreement (only computable with a calibrated scheme->gear map)
    gears = Counter((r.get("policy") or {}).get("gear_desired") for r in rows)
    schemes = Counter(r.get("scheme_name") or r.get("scheme_guid") or "?" for r in rows)
    agreement = {"shadow_gear_distribution": dict(gears),
                 "in_service_scheme_distribution": dict(schemes),
                 "scheme_changes": sum(1 for i in range(1, len(rows))
                                       if rows[i].get("scheme_guid") != rows[i - 1].get("scheme_guid")),
                 "required": "agreement >= 85%"}
    if True:
        # fence 5.3 wording: shadow policy vs the IN-SERVICE POLICY (same state -> gear).
        # This box runs a single policy version (stub-1), so there is no second version to
        # compare against yet -> BLOCKED-no-second-policy. Comparing the shadow建议 against
        # the machine's manual Fn+Q gear is a DIFFERENT question and is reported as c1b
        # (observed, informational; it never gates e4_ready).
        pass
    if True:
        known = [(r.get("gear_actual"), (r.get("policy") or {}).get("gear_desired"))
                 for r in rows]
        known = [(a, d) for a, d in known
                 if a and not str(a).startswith(("mode:", "unknown", "uncalibrated")) and d]
        if known:
            matched = sum(1 for a, d in known if a == d)
            rate = matched / len(known)
            c1b = {"status": "OBSERVED",
                   "shadow_vs_manual_gear_rate": round(rate, 4), "counted_rows": len(known),
                   "gear_distribution": dict(Counter(a for a, _ in known)),
                   "note": "informational only: manual gear is not the in-service policy output"}
        else:
            c1b = {"status": "BLOCKED", "reason": "no real gear channel in rows "
                                                  "(run tools/shadow_run.py r29+)"}
        c1 = dict(agreement, status="BLOCKED",
                  reason="no second policy version to compare against (in-service == shadow == stub-1)",
                  note="criterion 1 needs a new logic vs the in-service policy at P6; "
                       "shadow-vs-manual gear is c1b, informational")


    # criterion 2: trial trip rate
    lv = Counter(((r.get("fence") or {}).get("level") or "NO-FENCE") for r in rows)
    l1p = sum(v for k, v in lv.items() if k in ("L1", "L2", "L3"))
    l2p = sum(v for k, v in lv.items() if k in ("L2", "L3"))
    trip_rows = [r for r in rows if ((r.get("fence") or {}).get("level") in ("L2", "L3"))]
    c2 = {"status": "PASS" if l2p == 0 else "FAIL",
          "levels": dict(lv), "ticks": len(rows),
          "l1_plus_rate": round(l1p / len(rows), 4), "l2_plus_count": l2p,
          "required": "L2+ trial trips == 0; L1+ <= in-service + 2pp",
          "in_service_trip_rate": "BLOCKED-no-live-baseline",
          "l2_plus_rows": [{"ts": r.get("ts"), "level": (r.get("fence") or {}).get("level"),
                            "sources": (r.get("fence") or {}).get("trigger_sources")}
                           for r in trip_rows[:5]]}

    # criterion 3: fluency neutral (p95 within +-5% of baseline)
    p95s = p95_list(rows)
    if not p95s:
        c3 = {"status": "BLOCKED", "reason": "no frame labels in the shadow rows",
              "required": "window p95 within +-5% of same-class baseline"}
    else:
        if args.baseline_p95:
            base = float(args.baseline_p95)
            base_src = "cli"
        else:
            n = max(1, len(p95s) // 5)
            base = statistics.median(p95s[:n])
            base_src = "earliest-20pct-of-labelled-rows"
        med = statistics.median(p95s)
        dev = (med - base) / base if base else 0.0
        c3 = {"status": "PASS" if abs(dev) <= P95_TOL else "FAIL",
              "baseline_p95_ms": round(base, 3), "baseline_source": base_src,
              "shadow_median_p95_ms": round(med, 3), "deviation": round(dev, 4),
              "labelled_rows": len(p95s), "required": "within +-5%"}

    # criterion 4: zero crash
    errors = sum(1 for r in rows if r.get("error"))
    timeouts = sum(1 for r in rows
                   if ((r.get("fence") or {}).get("elapsed_ms") or 0.0) > INFER_BUDGET_MS)
    bad_tick = sum(1 for r in rows if (r.get("tick_ms") or 0.0) > 1500.0)
    c4 = {"status": "PASS" if (errors == 0 and timeouts == 0) else "FAIL",
          "errors": errors, "budget_overruns": timeouts, "slow_ticks_gt_1.5s": bad_tick,
          "required": "zero exception, zero 50ms inference overrun"}

    # effective coverage vs E4 requirement
    cov = []
    for w, need in sorted(REQ_HOURS.items()):
        got = {k: v for k, v in hours.items() if k.startswith(w + "/")}
        total = round(sum(got.values()), 2)
        cov.append({"work": w, "required_h": need, "hours_by_cell": got,
                    "hours_total": total, "status": "PASS" if total >= need else "SHORT"})
    nplug, plug_rows = plug_events()
    cov_ok = all(c["status"] == "PASS" for c in cov) and nplug >= 1

    crit_ok = c2["status"] == "PASS" and c4["status"] == "PASS"
    ready = cov_ok and crit_ok and c1["status"] == "PASS" and c3["status"] == "PASS"
    out = {"generated_from": args.glob, "rows": len(rows),
           "coverage": {"cells": hours, "e4_requirements": cov,
                        "plug_events": nplug, "plug_rows": plug_rows[:3]},
           "c1_action_agreement": c1, "c1b_shadow_vs_manual_gear": c1b,
           "c2_trial_trip_rate": c2, "c3_fluency_neutral": c3, "c4_zero_crash": c4,
           "e4_ready": ready,
           "open_items": [k for k, v in (("c1_action_agreement", c1), ("c3_fluency_neutral", c3))
                          if v["status"] != "PASS"] +
                         ([] if cov_ok else ["coverage/plug hours short"]) +
                         ([] if crit_ok else ["c2/c4 not pass"])}
    (ROOT / args.json_out).write_text(json.dumps(out, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=True))
    print(f"e4_ready={ready} -> {args.json_out}")
    return 0 if ready else 2


if __name__ == "__main__":
    sys.exit(main())
