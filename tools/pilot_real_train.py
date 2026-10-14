"""Real-data model pilot (r38): telemetry heads + frame-label perf head.

Replaces the r26 version which hardcoded part1+part2, used 2 features, and always wrote
perf_head=BLOCKED-no-frame-labels / grid=W0-only -- both are stale since the shadow link
started producing real gear labels and frame labels.

Two collections, reported separately and never mixed:

  A) telemetry  : every artifacts/datasets/D_safe_shadow_A_part*.csv row -> power / temp heads
                  (features: util, sm clock). Parts 1-4 contribute rows but carry a constant
                  gear label, so no gear claim is made for this set.
  B) frame-label: artifacts/samples/e4_shadow_*.jsonl rows that carry `frames` -> perf head
                  (features: util, sm clock, real gear index). Windows: the 2h game run plus
                  the 15min office run.

Honesty notes baked into the output:
  - this is a state->observation association model, NOT f(s,a): the collector has no action
    variable, and Action7 only exists inside the shadow trial.
  - every head is compared against the mean predictor on the same split; a head that loses to
    the mean is reported as such instead of being hidden.
"""
import csv
import glob
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "artifacts" / "datasets"
SAMPLES = ROOT / "artifacts" / "samples"
GEAR_IDX = {"Quiet": 0, "Balance": 1, "Beast": 2, "Extreme": 3}


def num(x):
    s = str(x).strip()
    if s in ("", "[N/A]", "N/A", "None"):
        return None
    for suf in (" %", "%", " MHz", "MHz", " W", "W"):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    try:
        return float(s)
    except ValueError:
        return None


def fit_eval(X, Y, seed=0, epochs=200, hidden=32):
    """Tiny MLP, 80/20 split; returns (rmse, mean_baseline, n)."""
    n = len(X)
    if n < 50:
        return None
    torch.manual_seed(seed)
    xm, xs = X.mean(0), X.std(0) + 1e-6
    ym, ys = Y.mean(0), Y.std(0) + 1e-6
    Xn = torch.tensor((X - xm) / xs, dtype=torch.float32)
    Yn = torch.tensor((Y - ym) / ys, dtype=torch.float32)
    n1 = int(n * 0.8)
    m = nn.Sequential(nn.Linear(X.shape[1], hidden), nn.ReLU(),
                      nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, Y.shape[1]))
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3)
    fn = nn.MSELoss()
    for _ in range(epochs):
        m.train()
        opt.zero_grad()
        fn(m(Xn[:n1]), Yn[:n1]).backward()
        opt.step()
    m.eval()
    with torch.no_grad():
        pred = (m(Xn[n1:]).numpy() * ys + ym)
    yt = Y[n1:]
    rmse = np.sqrt(np.mean((pred - yt) ** 2, axis=0)).tolist()
    base = np.sqrt(np.mean((ym - yt) ** 2, axis=0)).tolist()
    return ([round(v, 3) for v in rmse], [round(v, 3) for v in base], n)


# ---- set A: telemetry ---------------------------------------------------------------
XA, YA, gearA = [], [], []
for p in sorted(glob.glob(str(DATA / "D_safe_shadow_A_part*.csv"))):
    with open(p, newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            u = num(r.get("utilization.gpu [%]"))
            mhz = num(r.get("clocks.current.sm [MHz]"))
            pw = num(r.get("power.draw [W]"))
            tp = num(r.get("temperature.gpu"))
            if None in (u, mhz, pw, tp):
                continue
            XA.append([u, mhz / 1000.0])
            YA.append([pw, tp])
            gearA.append((r.get("gear_readonly") or "").strip())

XA = np.array(XA, dtype=np.float32)
YA = np.array(YA, dtype=np.float32)
out = {"set_A_telemetry": {"rows": int(len(XA)),
                           "features": ["util_pct", "sm_ghz"],
                           "targets": ["power_w", "temp_c"],
                           "gear_labels_present": sorted(set(gearA))[:6]}}

# per-work-cell split for honesty about distribution
if len(XA):
    gear_counts = {}
    for g in gearA:
        gear_counts[g] = gear_counts.get(g, 0) + 1
    out["set_A_telemetry"]["gear_row_counts_top"] = dict(
        sorted(gear_counts.items(), key=lambda kv: -kv[1])[:6])
    fA = fit_eval(XA, YA)
    if fA:
        out["set_A_telemetry"]["rmse_power_temp"] = fA[0]
        out["set_A_telemetry"]["mean_baseline"] = fA[1]
        out["set_A_telemetry"]["n_used"] = fA[2]

# ---- set B: frame labels from the shadow windows -------------------------------------
XB, YB, metaB = [], [], []
for p in sorted(glob.glob(str(SAMPLES / "e4_shadow_*.jsonl"))):
    if p.endswith("joined.jsonl"):
        pass  # joined files are the labelled ones; both forms are scanned on purpose
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
            p95 = fr.get("p95_ms")
            tel = r.get("telemetry") or {}
            u, mhz = tel.get("util_pct"), tel.get("clocks_sm_mhz")
            gear = r.get("gear_actual")
            if p95 is None or u is None or mhz is None or gear not in GEAR_IDX:
                continue
            XB.append([float(u), float(mhz) / 1000.0, float(GEAR_IDX[gear])])
            YB.append([float(p95)])
            metaB.append((r.get("work"), gear))

out["set_B_frame_labels"] = {"rows": int(len(XB)),
                             "features": ["util_pct", "sm_ghz", "gear_idx"],
                             "targets": ["frame_p95_ms"],
                             "windows": sorted(set(m[0] for m in metaB))}
if XB:
    XB = np.array(XB, dtype=np.float32)
    YB = np.array(YB, dtype=np.float32)
    fB = fit_eval(XB, YB)
    if fB:
        out["set_B_frame_labels"]["rmse_p95"] = fB[0]
        out["set_B_frame_labels"]["mean_baseline"] = fB[1]
        out["set_B_frame_labels"]["n_used"] = fB[2]
    by_gear = {}
    for (w, g) in metaB:
        by_gear[g] = by_gear.get(g, 0) + 1
    out["set_B_frame_labels"]["gear_row_counts"] = by_gear

out["perf_head"] = "REAL-frame-labels (set B)" if len(metaB) else "BLOCKED-no-frame-labels"
out["model_kind"] = "state->observation association (not f(s,a): no action variable in collection)"
out["grid"] = "multi-cell: " + ", ".join(sorted(set(
    f"{m[0]}/{m[1]}" for m in metaB))) if metaB else "no frame-label cells"
out["synthetic"] = False

(SAMPLES / "real_models.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
