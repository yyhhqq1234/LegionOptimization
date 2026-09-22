"""P4 training on synthetic D_safe (pipeline validation, NOT real)."""
import csv
import json
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "src"))
from policy.surrogate import MLP, Ensemble5, rank_loss, monotonic_penalty

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device={DEVICE}")

SRC = ROOT / "artifacts" / "samples" / "D_safe_synth_A_v1.csv"
rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
print(f"rows={len(rows)}")

# features: pl1, freq, cpu, gpu, is_game, is_DC, gear_idx, soc_proxy
GEAR_IDX = {"Quiet": 0, "Balance": 1, "Beast": 2, "Extreme": 3}
X, Y = [], []
for r in rows:
    X.append([float(r["pl1_w"]), float(r["freq_ghz"]), float(r["cpu_util"]), float(r["gpu_util"]),
              1.0 if r["work"] == "W2" else 0.0, 1.0 if r["acdc"] == "DC" else 0.0,
              float(GEAR_IDX[r["gear"]]), 80.0])
    Y.append([float(r["perf_score"]), float(r["power_w"]), float(r["temp_c"])])
X = torch.tensor(X, dtype=torch.float32)
Y = torch.tensor(Y, dtype=torch.float32)
# per-machine z-score (synthetic single machine)
xm, xs = X.mean(0), X.std(0) + 1e-6
ym, ys = Y.mean(0), Y.std(0) + 1e-6
Xn, Yn = (X - xm) / xs, (Y - ym) / ys

# time split 7:1:2
n = len(Xn)
n1, n2 = int(n * 0.7), int(n * 0.8)
tr, va, te = (Xn[:n1], Yn[:n1]), (Xn[n1:n2], Yn[n1:n2]), (Xn[n2:], Yn[n2:])
trl = DataLoader(TensorDataset(*tr), batch_size=256, shuffle=True)


def train_mlp(seed=0, epochs=30):
    torch.manual_seed(seed)
    m = MLP(8, 3).to(DEVICE)
    opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
    loss_fn = nn.MSELoss()
    best, patience, best_state = 1e9, 0, None
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
            pv = m(va[0].to(DEVICE))
            vl = loss_fn(pv, va[1].to(DEVICE)).item()
        if vl < best - 1e-4:
            best, patience, best_state = vl, 0, {k: v.cpu().clone() for k, v in m.state_dict().items()}
        else:
            patience += 1
            if patience >= 20:
                break
    m.load_state_dict(best_state)
    return m, best


mlp, mlp_val = train_mlp(0, epochs=30)
print(f"MLP val_mse={mlp_val:.4f}")

# 5-ensemble: train 5 seeds short, variance = uncertainty
members = []
for s in range(5):
    m, _ = train_mlp(s, epochs=15)
    members.append(m)
ens = Ensemble5(8, 3).to(DEVICE)
ens.members = torch.nn.ModuleList(members)

# metrics on test: RMSE/MAE per head (denormed)
mlp.eval()
with torch.no_grad():
    pt = mlp(te[0].to(DEVICE)).cpu() * ys + ym
    yt = te[1] * ys + ym
    rmse = (((pt - yt) ** 2).mean(0) ** 0.5).tolist()
    mae = (pt - yt).abs().mean(0).tolist()
print(f"MLP test RMSE perf/power/temp={rmse}")
print(f"MLP test MAE={mae}")

# Kendall tau on perf ranking (test)
def kendall(a, b):
    import itertools
    c = d = 0
    for i, j in itertools.combinations(range(min(200, len(a))), 2):
        sa = (a[i] - a[j]) > 0
        sb = (b[i] - b[j]) > 0
        if sa == sb:
            c += 1
        else:
            d += 1
    return (c - d) / max(1, c + d)

tau = kendall(pt[:, 0].tolist(), yt[:, 0].tolist())
print(f"Kendall tau perf={tau:.3f}")

# LightGBM: missing dep -> declaration (owner P4 to add before baseline)
try:
    import lightgbm  # noqa
    lgb_status = "available"
except ImportError:
    lgb_status = "MISSING (owner P4 to pip install before baseline; MLP/Ensemble used)"

# Export: try ONNX, fallback torchscript (onnx pkg missing per requirements)
OUT_DIR = ROOT / "artifacts" / "samples"
onnx_path = OUT_DIR / "predictor_v1.onnx"
ts_path = OUT_DIR / "predictor_v1.pt"
export_kind = "none"
try:
    import onnx  # noqa
    mlp.eval()
    dummy = torch.randn(1, 8)
    torch.onnx.export(mlp.cpu(), dummy, str(onnx_path), input_names=["x"], output_names=["y"],
                      dynamic_axes={"x": {0: "n"}, "y": {0: "n"}})
    export_kind = "onnx"
except ImportError:
    mlp.eval()
    ex = torch.jit.trace(mlp.cpu(), torch.randn(1, 8))
    ex.save(str(ts_path))
    export_kind = "torchscript-fallback (onnx pkg missing, M8 declaration)"

# latency: CPU <5ms check
mlp.cpu().eval()
t0 = time.perf_counter()
for _ in range(200):
    with torch.no_grad():
        mlp.cpu()(torch.randn(1, 8))
lat_ms = (time.perf_counter() - t0) / 200 * 1000
size_mb = (onnx_path.stat().st_size / 1e6) if onnx_path.exists() else (ts_path.stat().st_size / 1e6 if ts_path.exists() else 0)
print(f"export={export_kind} size={size_mb:.2f}MB latency={lat_ms:.2f}ms")

report = {
    "synthetic": True, "rows": len(rows), "device": DEVICE,
    "mlp_val_mse": mlp_val, "rmse": rmse, "mae": mae, "kendall_tau": tau,
    "lightgbm": lgb_status, "export": export_kind, "size_mb": size_mb, "latency_ms": lat_ms,
    "note": "synthetic pipeline only; real D_safe needs 5h+ collection; Return+10% on replay pending real B2 anchor",
}
(OUT_DIR / "p4_synth_compare.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("wrote p4_synth_compare.json")
