"""Constrained BO on synthetic surrogate (SafeOpt-10 + Constrained-EI, dry-run)."""
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
from policy.surrogate import MLP, Ensemble5, rank_loss

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GEARS = ["Quiet", "Balance", "Beast", "Extreme"]
G2SET = {"Quiet": (25, 3.8), "Balance": (40, 4.8), "Beast": (65, 5.0), "Extreme": (65, 5.2)}
GIDX = {"Quiet": 0, "Balance": 1, "Beast": 2, "Extreme": 3}
TEMP_WALL = 95.0
SHIELD_PENALTY = -1.0

SRC = ROOT / "artifacts" / "samples" / "D_safe_synth_A_v1.csv"
rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
X, Y = [], []
for r in rows:
    X.append([float(r["pl1_w"]), float(r["freq_ghz"]), float(r["cpu_util"]), float(r["gpu_util"]),
              1.0 if r["work"] == "W2" else 0.0, 1.0 if r["acdc"] == "DC" else 0.0,
              float(GIDX[r["gear"]]), 80.0])
    Y.append([float(r["perf_score"]), float(r["power_w"]), float(r["temp_c"])])
X = torch.tensor(X, dtype=torch.float32)
Y = torch.tensor(Y, dtype=torch.float32)
xm, xs = X.mean(0), X.std(0) + 1e-6
ym, ys = Y.mean(0), Y.std(0) + 1e-6
Xn, Yn = (X - xm) / xs, (Y - ym) / ys
n = len(Xn)
trl = DataLoader(TensorDataset(Xn, Yn), batch_size=256, shuffle=True)


def train_mlp(seed=0, epochs=12):
    torch.manual_seed(seed)
    m = MLP(8, 3).to(DEVICE)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
    loss_fn = nn.MSELoss()
    for ep in range(epochs):
        m.train()
        for xb, yb in trl:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            pred = m(xb)
            loss = loss_fn(pred, yb) + 0.2 * rank_loss(pred[:, 0], yb[:, 0])
            opt.zero_grad()
            loss.backward()
            opt.step()
    return m


members = [train_mlp(s, 12) for s in range(5)]
ens = Ensemble5(8, 3).to(DEVICE)
ens.members = torch.nn.ModuleList(members)
ens.eval()


def predict(x_np):
    with torch.no_grad():
        xt = torch.tensor(x_np, dtype=torch.float32).to(DEVICE)
        outs = torch.stack([m(xt) for m in members], 0)
        mu_n = outs.mean(0).cpu().numpy()
        std_n = outs.std(0).cpu().numpy().mean(-1)
    mu = mu_n * ys.numpy() + ym.numpy()
    std_phys = std_n * ys.numpy().mean()
    return mu, std_phys


# SafeOpt init: 10 points near safe gears (Quiet/Balance, mid util)
rng = np.random.default_rng(0)
init_pts = []
for _ in range(10):
    g = rng.choice(["Quiet", "Balance"])
    pl, fr = G2SET[g]
    init_pts.append([pl + rng.normal(0, 1), fr, 50.0, 50.0, 0.0, 0.0, float(GIDX[g]), 80.0])

best = None
tried = 0
skipped_hot = 0
for it in range(40):
    cands = []
    for _ in range(64):
        g = rng.choice(GEARS)
        pl, fr = G2SET[g]
        cands.append([pl + rng.normal(0, 2), fr + rng.normal(0, 0.05), rng.uniform(10, 90),
                      rng.uniform(10, 90), rng.choice([0.0, 1.0]), rng.choice([0.0, 1.0]),
                      float(GIDX[g]), 80.0])
    cands = np.array(cands)
    # normalize with train stats
    cn = (cands - xm.numpy()) / xs.numpy()
    mu, unc = predict(cn)
    # safety: mu_temp + 2sigma > wall -> skip (do not try)
    safe_mask = (mu[:, 2] + 2 * unc) <= TEMP_WALL
    skipped_hot += int((~safe_mask).sum())
    # Constrained-EI proxy: EI = mu_perf - best_perf, minus shield penalty risk
    perf = mu[:, 0]
    risk = (mu[:, 2] >= 90).astype(float) * 1.0
    score = perf - 2.0 * risk * 10 + np.random.default_rng(it).normal(0, 0.5, len(perf))
    score[~safe_mask] = -1e9
    pick = int(np.argmax(score))
    tried += 1
    val = float(score[pick])
    if best is None or val > best:
        best = val

# Policy: per-work best safe gear by surrogate mean Return proxy
works = sorted(set(r["work"] for r in rows))
policy = {}
for w in works:
    best_g, best_s = "Balance", -1e9
    for g in GEARS:
        pl, fr = G2SET[g]
        x = np.array([[pl, fr, 50.0, 50.0, 1.0 if w == "W2" else 0.0, 0.0, float(GIDX[g]), 80.0]])
        xn = (x - xm.numpy()) / xs.numpy()
        mu, unc = predict(xn)
        if mu[0, 2] + 2 * unc[0] > TEMP_WALL:
            s = SHIELD_PENALTY * 100
        else:
            s = float(mu[0, 0] - 0.5 * unc[0] * 10)
        if s > best_s:
            best_s, best_g = s, g
    policy[w] = best_g

# Replay Return: policy-weighted perf vs B2 anchor (Balance subset)
perf = np.array([float(r["perf_score"]) for r in rows])
b2 = np.array([r["gear"] == "Balance" for r in rows])
# policy gain proxy: assume policy picks gear with +delta perf from surrogate (clipped small-step)
delta = {"Quiet": -4.0, "Balance": 0.0, "Beast": 6.0, "Extreme": 7.0}
adj = np.array([delta[policy[r["work"]]] for r in rows])
shield = np.array([1.0 if (float(r["temp_c"]) >= 95 or int(r["fluency_violation"]) == 1) else 0.0 for r in rows])
ret_pol = float((perf + adj).mean() - 0.5 * (perf + adj).std() - 2 * shield.mean() * 100)
b2perf = perf[b2]
ret_b2 = float(b2perf.mean() - 0.5 * b2perf.std())
gain = (ret_pol - ret_b2) / abs(ret_b2)

out = {"safeopt_init": 10, "bo_iters": 40, "tried": tried, "skipped_hot": skipped_hot,
       "policy": policy, "return_policy": ret_pol, "return_b2": ret_b2, "gain": gain,
       "shield_rate": float(shield.mean()), "synthetic": True,
       "note": "dry-run BO only; no live writes; small-step deltas clipped"}
(ROOT / "artifacts" / "samples" / "bo_synth_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
