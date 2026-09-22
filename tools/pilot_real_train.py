"""Pilot: fit power/temp heads on REAL shadow rows (no perf label yet, honest)."""
import csv
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parent.parent


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


X, Y = [], []
for part in ("D_safe_shadow_A_part1.csv", "D_safe_shadow_A_part2.csv"):
    p = ROOT / "artifacts" / "datasets" / part
    if not p.exists():
        continue
    for r in csv.DictReader(p.open(encoding="utf-8")):
        u = num(r.get("utilization.gpu [%]"))
        mhz = num(r.get("clocks.current.sm [MHz]"))
        pw = num(r.get("power.draw [W]"))
        tp = num(r.get("temperature.gpu"))
        if None in (u, mhz, pw, tp):
            continue
        X.append([u, mhz / 1000.0])
        Y.append([pw, tp])
X = np.array(X, dtype=np.float32)
Y = np.array(Y, dtype=np.float32)
n = len(X)
print(f"real usable rows={n}")
assert n >= 100, "too few real rows"

xm, xs = X.mean(0), X.std(0) + 1e-6
ym, ys = Y.mean(0), Y.std(0) + 1e-6
Xn = torch.tensor((X - xm) / xs)
Yn = torch.tensor((Y - ym) / ys)
n1 = int(n * 0.8)
m = nn.Sequential(nn.Linear(2, 32), nn.ReLU(), nn.Linear(32, 32), nn.ReLU(), nn.Linear(32, 2))
opt = torch.optim.AdamW(m.parameters(), lr=3e-3)
fn = nn.MSELoss()
for ep in range(100):
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
out = {"n": n, "rmse_power_temp": [round(v, 3) for v in rmse],
       "mean_baseline": [round(v, 3) for v in base],
       "perf_head": "BLOCKED-no-frame-labels",
       "grid": "W0/AC-only", "synthetic": False}
(ROOT / "artifacts" / "samples" / "real_pilot.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
