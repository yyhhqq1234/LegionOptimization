"""Cross-machine test: train on A, test on B (independent z-score, whole-machine leave-one-out)."""
import csv
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "src"))
from policy.surrogate import MLP, rank_loss

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GIDX = {"Quiet": 0, "Balance": 1, "Beast": 2, "Extreme": 3}


def load(path):
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8")))
    X, Y = [], []
    for r in rows:
        X.append([float(r["pl1_w"]), float(r["freq_ghz"]), float(r["cpu_util"]), float(r["gpu_util"]),
                  1.0 if r["work"] == "W2" else 0.0, 1.0 if r["acdc"] == "DC" else 0.0,
                  float(GIDX[r["gear"]]), 80.0])
        Y.append([float(r["perf_score"]), float(r["power_w"]), float(r["temp_c"])])
    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.float32)


Xa, Ya = load(ROOT / "artifacts" / "samples" / "D_safe_synth_A_v1.csv")
Xb, Yb = load(ROOT / "artifacts" / "samples" / "D_safe_synth_B_v1.csv")
# independent z-score per machine (P4 spec)
xam, xas = Xa.mean(0), Xa.std(0) + 1e-6
yam, yas = Ya.mean(0), Ya.std(0) + 1e-6
xbm, xbs = Xb.mean(0), Xb.std(0) + 1e-6
ybm, ybs = Yb.mean(0), Yb.std(0) + 1e-6
Xtr = torch.tensor((Xa - xam) / xas)
Ytr = torch.tensor((Ya - yam) / yas)
Xte = torch.tensor((Xb - xbm) / xbs)
Yte = torch.tensor((Yb - ybm) / ybs)

trl = DataLoader(TensorDataset(Xtr, Ytr), batch_size=256, shuffle=True)
torch.manual_seed(0)
m = MLP(8, 3).to(DEVICE)
opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
fn = nn.MSELoss()
for ep in range(25):
    m.train()
    for xb, yb in trl:
        xb, yb = xb.to(DEVICE), yb.to(DEVICE)
        p = m(xb)
        loss = fn(p, yb) + 0.2 * rank_loss(p[:, 0], yb[:, 0])
        opt.zero_grad()
        loss.backward()
        opt.step()

m.eval()
with torch.no_grad():
    # test on B with B z-score, denorm with B stats
    pn = m(Xte.to(DEVICE)).cpu().numpy()
    pd = pn * ybs + ybm
    rmse = (np.sqrt(np.mean((pd - Yb) ** 2, axis=0))).tolist()
    mae = (np.mean(np.abs(pd - Yb), axis=0)).tolist()
    # same-machine reference: train/test split on A only (last 20% of A)
    n = len(Xtr)
    Xav = Xtr[int(n * 0.8):].to(DEVICE)
    Yav = (Ytr[int(n * 0.8):].numpy() * yas + yam)
    pav = m(Xav).cpu().numpy() * yas + yam
    rmse_a = (np.sqrt(np.mean((pav - Yav) ** 2, axis=0))).tolist()

out = {"train": "A-2000", "test": "B-1200-whole-machine",
       "rmse_cross_AB": rmse, "mae_cross_AB": mae, "rmse_same_A": rmse_a,
       "shift_note": "B hotter +4C, power x1.05 (heterogeneous proxy)",
       "synthetic": True}
(ROOT / "artifacts" / "samples" / "cross_AB.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
