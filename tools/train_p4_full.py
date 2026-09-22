"""P4 full: LightGBM baseline + MLP + Ensemble + ONNX + coverage + Return."""
import csv
import json
import time
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
SRC = ROOT / "artifacts" / "samples" / "D_safe_synth_A_v1.csv"
rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
GEAR_IDX = {"Quiet": 0, "Balance": 1, "Beast": 2, "Extreme": 3}
X, Y, GRID, INTER = [], [], {}, 0
for r in rows:
    X.append([float(r["pl1_w"]), float(r["freq_ghz"]), float(r["cpu_util"]), float(r["gpu_util"]),
              1.0 if r["work"] == "W2" else 0.0, 1.0 if r["acdc"] == "DC" else 0.0,
              float(GEAR_IDX[r["gear"]]), 80.0])
    Y.append([float(r["perf_score"]), float(r["power_w"]), float(r["temp_c"])])
    key = (r["work"], r["acdc"])
    GRID[key] = GRID.get(key, 0) + 1
    # synthetic interactive proxy: W1/W6 office/browser rows count as interactive
    if r["work"] in ("W1", "W6"):
        INTER += 1
X = torch.tensor(X, dtype=torch.float32)
Y = torch.tensor(Y, dtype=torch.float32)
cells, covered = 16, sum(1 for v in GRID.values() if v >= 80)
coverage = covered / 16
inter_ratio = INTER / len(rows)
print(f"grid covered {covered}/16={coverage:.2f} interactive={inter_ratio:.2f}")

xm, xs = X.mean(0), X.std(0) + 1e-6
ym, ys = Y.mean(0), Y.std(0) + 1e-6
Xn, Yn = (X - xm) / xs, (Y - ym) / ys
n = len(Xn)
n1, n2 = int(n * 0.7), int(n * 0.8)
tr, va, te = (Xn[:n1], Yn[:n1]), (Xn[n1:n2], Yn[n1:n2]), (Xn[n2:], Yn[n2:])
trl = DataLoader(TensorDataset(*tr), batch_size=256, shuffle=True)


def train_mlp(seed=0, epochs=30):
    torch.manual_seed(seed)
    m = MLP(8, 3).to(DEVICE)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
    loss_fn = nn.MSELoss()
    best, pat, best_state = 1e9, 0, None
    for ep in range(epochs):
        m.train()
        for xb, yb in trl:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            pred = m(xb)
            loss = loss_fn(pred, yb) + 0.2 * rank_loss(pred[:, 0], yb[:, 0])
            opt.zero_grad()
            loss.backward()
            opt.step()
        m.eval()
        with torch.no_grad():
            vl = loss_fn(m(va[0].to(DEVICE)), va[1].to(DEVICE)).item()
        if vl < best - 1e-4:
            best, pat, best_state = vl, 0, {k: v.cpu().clone() for k, v in m.state_dict().items()}
        else:
            pat += 1
            if pat >= 20:
                break
    m.load_state_dict(best_state)
    return m


mlp = train_mlp(0, 30)
members = [train_mlp(s, 12) for s in range(5)]

# LightGBM baseline: 3 heads (perf/power/temp), same split
import lightgbm as lgb
Xn_np, Yn_np = Xn.numpy(), Yn.numpy()
lgb_rmses, lgb_maes = [], []
for h in range(3):
    dtrain = lgb.Dataset(Xn_np[:n1], label=Yn_np[:n1, h])
    dvalid = lgb.Dataset(Xn_np[n1:n2], label=Yn_np[n1:n2, h], reference=dtrain)
    params = {"objective": "regression", "metric": "rmse", "verbosity": -1, "num_leaves": 31}
    bst = lgb.train(params, dtrain, num_boost_round=300,
                    valid_sets=[dvalid],
                    callbacks=[lgb.early_stopping(20, verbose=False)])
    pred = bst.predict(Xn_np[n2:])
    # denorm
    pred_d = pred * float(ys[h]) + float(ym[h])
    yt_d = Yn_np[n2:, h] * float(ys[h]) + float(ym[h])
    rmse = float(np.sqrt(np.mean((pred_d - yt_d) ** 2)))
    mae = float(np.mean(np.abs(pred_d - yt_d)))
    lgb_rmses.append(rmse)
    lgb_maes.append(mae)
print(f"LGB RMSE {lgb_rmses} MAE {lgb_maes}")

# MLP metrics denormed
mlp.eval()
with torch.no_grad():
    pt = mlp(te[0].to(DEVICE)).cpu() * ys + ym
    yt = te[1] * ys + ym
    mlp_rmse = (((pt - yt) ** 2).mean(0) ** 0.5).tolist()
    mlp_mae = (pt - yt).abs().mean(0).tolist()
print(f"MLP RMSE {mlp_rmse} MAE {mlp_mae}")

# Ensemble metrics
ens = Ensemble5(8, 3).to(DEVICE)
ens.members = torch.nn.ModuleList(members)
ens.eval()
with torch.no_grad():
    outs = torch.stack([m(te[0].to(DEVICE)) for m in members], 0)
    pe = outs.mean(0).cpu() * ys + ym
    ens_rmse = (((pe - yt) ** 2).mean(0) ** 0.5).tolist()
print(f"ENS RMSE {ens_rmse} unc_mean={outs.var(0).mean().item():.4f}")

# Kendall tau perf
def kendall(a, b):
    import itertools
    c = d = 0
    idx = list(range(min(200, len(a))))
    for i, j in itertools.combinations(idx, 2):
        if ((a[i] - a[j]) > 0) == ((b[i] - b[j]) > 0):
            c += 1
        else:
            d += 1
    return (c - d) / max(1, c + d)

tau_mlp = kendall(pt[:, 0].tolist(), yt[:, 0].tolist())
print(f"tau_mlp={tau_mlp:.3f}")

# ONNX export (real) + latency + size
OUT = ROOT / "artifacts" / "samples"
onnx_path = OUT / "predictor_v1.onnx"
mlp.cpu().eval()
torch.onnx.export(mlp.cpu(), torch.randn(1, 8), str(onnx_path),
                  input_names=["x"], output_names=["y"],
                  dynamic_axes={"x": {0: "n"}, "y": {0: "n"}})
import onnxruntime as ort
sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
t0 = time.perf_counter()
for _ in range(200):
    sess.run(None, {"x": np.random.randn(1, 8).astype(np.float32)})
lat = (time.perf_counter() - t0) / 200 * 1000
size_mb = onnx_path.stat().st_size / 1e6
print(f"ONNX size={size_mb:.2f}MB lat={lat:.2f}ms")

# Return replay (synthetic): Return = mean-0.5std-2shield-1clamp
# shield proxy: temp>95 or fluency flag; clamp proxy: gear Extreme power>100
perf = np.array([float(r["perf_score"]) for r in rows])
shield = np.array([1.0 if (float(r["temp_c"]) >= 95 or int(r["fluency_violation"]) == 1) else 0.0 for r in rows])
clamp = np.array([1.0 if (r["gear"] == "Extreme" and float(r["power_w"]) > 100) else 0.0 for r in rows])
ret = float(perf.mean() - 0.5 * perf.std() - 2 * shield.mean() * 100 - 1 * clamp.mean() * 100)
# B2 anchor: synthetic B2 = Balance-gear subset mean as proxy anchor
b2mask = np.array([r["gear"] == "Balance" for r in rows])
b2perf = perf[b2mask]
b2ret = float(b2perf.mean() - 0.5 * b2perf.std())
gain = (ret - b2ret) / abs(b2ret)
print(f"Return={ret:.1f} B2anchor={b2ret:.1f} gain={gain * 100:.1f}% shield_rate={shield.mean():.4f}")

report = {"synthetic": True, "rows": len(rows), "coverage_16": coverage,
          "interactive_ratio": inter_ratio, "mlp_rmse": mlp_rmse, "mlp_mae": mlp_mae,
          "lgb_rmse": lgb_rmses, "lgb_mae": lgb_maes, "ens_rmse": ens_rmse,
          "tau_mlp": tau_mlp, "onnx_mb": size_mb, "onnx_lat_ms": lat,
          "return": ret, "b2_anchor": b2ret, "gain": gain, "shield_rate": float(shield.mean())}
(OUT / "p4_full_compare.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("wrote p4_full_compare.json")
