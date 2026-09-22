"""V12 proxy: B2 frozen configs x surrogate -> reward_baseline_B2.csv (B2 logs missing, honest proxy)."""
import csv
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "src"))
from policy.surrogate import MLP

# B2 frozen (thesis 0.4/G1 + envelope gears; logs missing per kickoff gap list)
B2 = {"Quiet": (25, 3.8), "Balance": (40, 4.8), "Beast": (65, 5.0), "Extreme": (65, 5.2)}
WORKS = ["W0", "W1", "W2", "W3", "W4", "W5", "W6", "W7"]
GIDX = {"Quiet": 0, "Balance": 1, "Beast": 2, "Extreme": 3}

ckpt = ROOT / "artifacts" / "samples" / "D_safe_synth_A_v1.csv"
rows = list(csv.DictReader(ckpt.open(encoding="utf-8")))
X = np.array([[float(r["pl1_w"]), float(r["freq_ghz"]), float(r["cpu_util"]), float(r["gpu_util"]),
               1.0 if r["work"] == "W2" else 0.0, 1.0 if r["acdc"] == "DC" else 0.0,
               float(GIDX[r["gear"]]), 80.0] for r in rows], dtype=np.float32)
Y = np.array([[float(r["perf_score"]), float(r["power_w"]), float(r["temp_c"])] for r in rows], dtype=np.float32)
xm, xs = X.mean(0), X.std(0) + 1e-6
ym, ys = Y.mean(0), Y.std(0) + 1e-6
Xn = torch.tensor((X - xm) / xs)
Yn = torch.tensor((Y - ym) / ys)

import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
torch.manual_seed(0)
m = MLP(8, 3)
opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
fn = nn.MSELoss()
dl = DataLoader(TensorDataset(Xn, Yn), batch_size=256, shuffle=True)
for _ in range(20):
    m.train()
    for xb, yb in dl:
        opt.zero_grad()
        fn(m(xb), yb).backward()
        opt.step()
m.eval()

OUT = ROOT / "artifacts" / "samples" / "reward_baseline_B2.csv"
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["gear", "work", "pl1_w", "freq_ghz", "pred_perf", "pred_power", "pred_temp",
                "shield", "clamp", "return", "proxy", "policy_ver", "fence_ver", "envelope_ver"])
    rets = []
    for g, (pl, fr) in B2.items():
        for wo in WORKS:
            x = np.array([[pl, fr, 50.0, 50.0, 1.0 if wo == "W2" else 0.0, 0.0, float(GIDX[g]), 80.0]], dtype=np.float32)
            with torch.no_grad():
                p = (m(torch.tensor((x - xm) / xs)).numpy() * ys + ym)[0]
            perf, power, temp = [float(v) for v in p]
            shield = 1.0 if temp >= 95 else 0.0
            clamp = 1.0 if (g == "Extreme" and power > 100) else 0.0
            ret = perf - 2 * shield * 100 - 1 * clamp * 100
            rets.append(ret)
            w.writerow([g, wo, pl, fr, round(perf, 2), round(power, 2), round(temp, 2),
                        shield, clamp, round(ret, 2), "B2-frozen-x-surrogate", "stub-1", "1.0", "1.0"])
rets = np.array(rets)
print(f"V12 proxy rows=32 Return mean={rets.mean():.1f} std={rets.std():.1f} "
      f"p10={np.quantile(rets, .1):.1f} p50={np.quantile(rets, .5):.1f} p90={np.quantile(rets, .9):.1f}")
print(f"wrote {OUT} (B0/B1/V10/V11 blocked: stock/LLT logs missing; B2 logs missing -> frozen-config proxy)")
