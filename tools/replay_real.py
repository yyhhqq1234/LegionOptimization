"""Real-data Return replay (r41): replay the reward over REAL frame-labelled rows.

Reward form is taken from tools/reward_baseline_B2.py so the two numbers are at least
computed the same way:

    ret_i = perf_i - 2*shield_i*100 - 1*clamp_i*100
    shield_i = 1 if temp >= 95 (B2 script)     clamp_i = 1 if gear == Extreme and power > 100

and the aggregate reported is mean / p10 / p50 / p90 of those per-row returns.

What the real side has to substitute (all labelled in the output):

  perf   : real data has no perf_score. It is derived as 100*clip(fps/target_fps,0,1) using the
           frame labels; rows without frame labels are excluded, so the replay covers the
           frame-labelled subset only (game window + office window).
  shield : the CPU temperature channel does not exist pre-E5, so the shield test uses the GPU
           temperature alone - a GPU-only proxy, stricter inputs were not available.
  target : spec gives target frames for W4 (120) / W5 (90); a game target of 120 is assumed here
           and printed, since W2 has no explicit value.

Verdict policy: this script refuses to present the number as Return acceptance evidence and
says why. The E4 shadow issues no actuation (dry-run), so a replay cannot separate the policy's
contribution from the environment; the honest comparison needs either a policy-acted replay or
the live canary. Comparisons are also cross-source (fps-derived perf vs model-predicted perf).
"""
import argparse
import csv
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "artifacts" / "samples"
sys.path.insert(0, str(ROOT / "src"))
from actuate.hal_map import GEAR_PL_W   # noqa: E402

GEAR_IDX = {"Quiet": 0, "Balance": 1, "Beast": 2, "Extreme": 3}


def clip01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def load_real_rows(pattern="artifacts/samples/e4_shadow_*.jsonl"):
    rows = []
    for p in sorted(glob.glob(str(ROOT / pattern))):
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                fr = r.get("frames") or {}
                fps = fr.get("fps")
                if fps is None:
                    continue
                tel = r.get("telemetry") or {}
                rows.append({"ts": r.get("ts"), "work": r.get("work"), "acdc": r.get("acdc_sensed") or r.get("acdc"),
                             "gear": r.get("gear_actual"), "fps": float(fps),
                             "power": tel.get("power_w"), "temp": tel.get("temp_c"),
                             "p95": fr.get("p95_ms")})
    return rows


def load_b2_baseline(path=None):
    path = Path(path) if path else (SAMPLES / "reward_baseline_B2.csv")
    rets = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rets.append(float(r["return"]))
            except (TypeError, ValueError):
                continue
    return rets, path


def stats(xs):
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)

    def q(p):
        return xs[min(n - 1, int(p * (n - 1)))]
    return {"n": n, "mean": round(sum(xs) / n, 2), "p10": round(q(0.1), 2),
            "p50": round(q(0.5), 2), "p90": round(q(0.9), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="artifacts/samples/e4_shadow_*.jsonl")
    ap.add_argument("--target-fps", type=float, default=120.0,
                    help="game target frames for the perf conversion (spec gives W4=120/W5=90)")
    ap.add_argument("--json-out", default="artifacts/samples/replay_real.json")
    args = ap.parse_args()

    rows = load_real_rows(args.glob)
    if not rows:
        print(f"no frame-labelled rows matched {args.glob}")
        return 1

    per_work, per_gear = {}, {}
    rets, shields, clamps, sat = [], 0, 0, 0
    for r in rows:
        if r["gear"] not in GEAR_IDX:      # unmapped gear -> cannot attribute a gear-derived pl1
            continue
        perf = 100.0 * clip01(r["fps"] / args.target_fps)
        shield = 1 if (r["temp"] is not None and float(r["temp"]) >= 95.0) else 0
        clamp = 1 if (r["gear"] == "Extreme" and r["power"] is not None
                      and float(r["power"]) > 100.0) else 0
        ret = perf - 2 * shield * 100 - 1 * clamp * 100
        rets.append(ret)
        shields += shield
        clamps += clamp
        if perf >= 99.999:
            sat += 1
        w = r["work"] or "?"
        g = r["gear"]
        per_work.setdefault(w, []).append(ret)
        per_gear.setdefault(g, []).append(ret)

    b2, b2_path = load_b2_baseline()
    real_stats, b2_stats = stats(rets), stats(b2)
    out = {"rows_frame_labelled": len(rows), "rows_used": len(rets),
           "reward_form": "perf - 2*shield*100 - 1*clamp*100 (same form as reward_baseline_B2.py)",
           "substitutions": {
               "perf": f"100*clip(fps/{args.target_fps:g},0,1) from frame labels (no perf_score in real data)",
               "shield": "GPU temperature >= 95C only (CPU channel missing pre-E5)",
               "target_fps": args.target_fps,
               "gear": "rows without an unmapped real gear excluded"},
           "real_return": real_stats,
           "real_shield_rows": shields, "real_clamp_rows": clamps,
           "real_by_work": {k: stats(v) for k, v in sorted(per_work.items())},
           "real_by_gear": {k: stats(v) for k, v in sorted(per_gear.items())},
           "b2_anchor": b2_stats, "b2_source": str(b2_path.relative_to(ROOT))}
    out["perf_saturation_rows"] = sat
    out["perf_saturation_rate"] = round(sat / max(1, len(rets)), 4)
    out["perf_definition_caveat"] = (
        "fps-derived perf saturates once fps exceeds the target (every game row reads 100 here), "
        "and the spec defines non-game perf as responsiveness rather than frames, so the W0/W1 "
        "groups are not comparable under this conversion")
    if real_stats and b2_stats and b2_stats["mean"]:
        nominal = (real_stats["mean"] - b2_stats["mean"]) / abs(b2_stats["mean"])
        out["nominal_gain"] = round(nominal, 4)
    out["verdict"] = "NOT-ACCEPTANCE-EVIDENCE"
    out["verdict_reasons"] = [
        f"perf saturates for every game row: target {args.target_fps:g}fps sits below the "
        "measured ~159fps, so the gain largely reflects a saturated perf term, not policy value",
        "E4 shadow is dry-run: no actuation, so the replay cannot separate the policy's "
        "contribution from the environment (same reason c3 is BLOCKED inside P4)",
        "cross-source comparison: real perf is derived from fps while the B2 anchor is a "
        "surrogate prediction over a frozen config - the two are not the same quantity",
        "environment is not matched: real rows were collected in Beast gear on the "
        "high-performance plan, the B2 anchor carries no such state",
        "shield test only sees the GPU (CPU channel absent), so the shield term is a lower bound",
    ]
    out["unlock"] = ("Return acceptance needs a policy-acted replay (a version that actually "
                     "issues setpoints) or the live canary; this script stays a magnitude check.")

    (ROOT / args.json_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=True))
    print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
