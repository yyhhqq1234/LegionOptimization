"""Real-data three-model compare (r40): MLP vs LightGBM vs 5-Ensemble on REAL rows.

Why a separate script: train_p4_full.py is the synthetic pipeline (D_safe_synth_A_v1.csv with
pl1_w / cpu_util / perf_score columns). Real collection has DIFFERENT reality:

  features available : sm clock (GHz), gpu util, work==W2 flag, DC flag, real gear index
  features MISSING   : cpu_util (no channel pre-E5), pl1_w (not sampled; derivable from the gear)
  targets            : power_w, temp_c always; fps only where frame labels exist

So two groups are trained and reported separately, and every substitution is labelled:

  group A (telemetry, all parts)      X = [sm_ghz, gpu_util, is_W2, is_DC]           -> power, temp
  group B (frame-label subset)        X = [pl1_from_gear, sm_ghz, gpu_util, is_W2,
                                           is_DC, gear_idx]                           -> fps, power, temp

  pl1_from_gear is a GEAR-DERIVED proxy (hal_map.GEAR_PL_W), not a measurement - flagged below.
  Rows whose gear column is the legacy constant are excluded from group B by construction
  (they cannot carry a gear index) and stay in group A as telemetry only.

Output: artifacts/samples/real_three_model.json (per-group MLP/LGB/ENS RMSE, MAE, tau).
"""
import csv
import glob
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from actuate.hal_map import GEAR_PL_W          # noqa: E402
from policy.surrogate import MLP, Ensemble5, rank_loss   # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DATA = ROOT / "artifacts" / "datasets"
SAMPLES = ROOT / "artifacts" / "samples"
OUT = SAMPLES / "real_three_model.json"
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


def load_group_a():
    X, Y = [], []
    for p in sorted(glob.glob(str(DATA / "D_safe_shadow_A_part*.csv"))):
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                u = num(r.get("utilization.gpu [%]"))
                mhz = num(r.get("clocks.current.sm [MHz]"))
                pw = num(r.get("power.draw [W]"))
                tp = num(r.get("temperature.gpu"))
                if None in (u, mhz, pw, tp):
                    continue
                X.append([mhz / 1000.0, u,
                          1.0 if (r.get("work") == "W2") else 0.0,
                          1.0 if (r.get("acdc") == "DC") else 0.0])
                Y.append([pw, tp])
    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.float32)


def load_group_b():
    X, Y = [], []
    for p in sorted(glob.glob(str(SAMPLES / "e4_shadow_*.jsonl"))):
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
                tel = r.get("telemetry") or {}
                fps = fr.get("fps")
                gear = r.get("gear_actual")
                u, mhz = tel.get("util_pct"), tel.get("clocks_sm_mhz")
                pw, tp = tel.get("power_w"), tel.get("temp_c")
                if None in (fps, u, mhz, pw, tp) or gear not in GEAR_IDX:
                    continue
                X.append([float(GEAR_PL_W[gear]), mhz / 1000.0, float(u),
                          1.0 if r.get("work") == "W2" else 0.0,
                          1.0 if r.get("acdc_sensed") == "DC" else 0.0,
                          float(GEAR_IDX[gear])])
                Y.append([float(fps), float(pw), float(tp)])
    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.float32)


def kendall(a, b, cap=200):
    idx = list(range(min(cap, len(a))))
    c = d = 0
    for i, j in itertools.combinations(idx, 2):
        if ((a[i] - a[j]) > 0) == ((b[i] - b[j]) > 0):
            c += 1
        else:
            d += 1
    return (c - d) / max(1, c + d)


def run_group(name, X, Y, out_dim):
    res = {"name": name, "rows": int(len(X)), "in_dim": int(X.shape[1]), "out_dim": out_dim}
    if len(X) < 200:
        res["status"] = "SKIPPED-too-few-rows"
        return res
    Xt = torch.tensor(X, dtype=torch.float32)
    Yt = torch.tensor(Y, dtype=torch.float32)
    xm, xs = Xt.mean(0), Xt.std(0) + 1e-6
    ym, ys = Yt.mean(0), Yt.std(0) + 1e-6
    Xn, Yn = (Xt - xm) / xs, (Yt - ym) / ys
    n = len(Xn)
    n1, n2 = int(n * 0.7), int(n * 0.8)
    tr = DataLoader(TensorDataset(Xn[:n1], Yn[:n1]), batch_size=256, shuffle=True)
    va = (Xn[n1:n2], Yn[n1:n2])
    te = (Xn[n2:], Yn[n2:])
    print(f"[{name}] rows={n} in_dim={X.shape[1]} out_dim={out_dim}")

    def train_mlp(seed=0, epochs=30):
        torch.manual_seed(seed)
        m = MLP(X.shape[1], out_dim).to(DEVICE)
        opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
        loss_fn = nn.MSELoss()
        best, pat, best_state = 1e9, 0, None
        for _ in range(epochs):
            m.train()
            for xb, yb in tr:
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
    pt = mlp(te[0].to(DEVICE)).cpu() * ys + ym
    yt = te[1] * ys + ym
    res["mlp_rmse"] = [round(v, 3) for v in (((pt - yt) ** 2).mean(0) ** 0.5).tolist()]
    res["mlp_mae"] = [round(v, 3) for v in (pt - yt).abs().mean(0).tolist()]
    res["mean_baseline"] = [round(v, 3) for v in (((ym - yt) ** 2).mean(0) ** 0.5).tolist()]
    res["tau_head0"] = round(kendall(pt[:, 0].tolist(), yt[:, 0].tolist()), 3)

    members = [train_mlp(s, 12) for s in range(5)]
    with torch.no_grad():
        outs = torch.stack([m(te[0].to(DEVICE)) for m in members], 0)
    pe = outs.mean(0).cpu() * ys + ym
    res["ens_rmse"] = [round(v, 3) for v in (((pe - yt) ** 2).mean(0) ** 0.5).tolist()]
    res["ens_unc_mean"] = round(float(outs.var(0).mean()), 5)
    pe_p95 = pe[:, 0] + 1.645 * (outs.std(0)[:, 0].cpu() * ys[0]).mean()
    res["ens_p95_over"] = round(float(pe_p95.mean()), 3)

    import lightgbm as lgb
    Xn_np, Yn_np = Xn.numpy(), Yn.numpy()
    lgb_rmse, lgb_mae = [], []
    for h in range(out_dim):
        dtrain = lgb.Dataset(Xn_np[:n1], label=Yn_np[:n1, h])
        dvalid = lgb.Dataset(Xn_np[n1:n2], label=Yn_np[n1:n2, h], reference=dtrain)
        bst = lgb.train({"objective": "regression", "metric": "rmse", "verbosity": -1,
                         "num_leaves": 31}, dtrain, num_boost_round=300,
                        valid_sets=[dvalid],
                        callbacks=[lgb.early_stopping(20, verbose=False)])
        pred = bst.predict(Xn_np[n2:]) * float(ys[h]) + float(ym[h])
        ytd = Yn_np[n2:, h] * float(ys[h]) + float(ym[h])
        lgb_rmse.append(round(float(np.sqrt(np.mean((pred - ytd) ** 2))), 3))
        lgb_mae.append(round(float(np.mean(np.abs(pred - ytd))), 3))
    res["lgb_rmse"] = lgb_rmse
    res["lgb_mae"] = lgb_mae

    # ONNX export of the real-data MLP + latency
    mlp.cpu().eval()
    onnx_path = SAMPLES / f"predictor_real_{name}.onnx"
    torch.onnx.export(mlp, torch.randn(1, X.shape[1]), str(onnx_path),
                      input_names=["x"], output_names=["y"],
                      dynamic_axes={"x": {0: "n"}, "y": {0: "n"}})
    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    t0 = time.perf_counter()
    for _ in range(200):
        sess.run(None, {"x": np.random.randn(1, X.shape[1]).astype(np.float32)})
    res["onnx_mb"] = round(onnx_path.stat().st_size / 1e6, 3)
    res["onnx_lat_ms"] = round((time.perf_counter() - t0) / 200 * 1000, 3)
    res["status"] = "ok"
    print(f"  MLP {res['mlp_rmse']} | LGB {res['lgb_rmse']} | ENS {res['ens_rmse']} "
          f"| baseline {res['mean_baseline']} | ONNX {res['onnx_mb']}MB {res['onnx_lat_ms']}ms")
    return res


report = {"synthetic": False,
          "feature_notes": {
              "cpu_util": "MISSING in real collection (no channel pre-E5) - not used",
              "pl1_w": "not sampled; group B uses GEAR_PL_W[gear] as a labelled proxy",
              "perf_head": "fps from frame labels (group B only); no perf_score exists in real data",
              "gear_column": "legacy constant rows are excluded from group B by construction"},
          "groups": []}

XA, YA = load_group_a()
report["groups"].append(run_group("A_telemetry", XA, YA, 2))
XB, YB = load_group_b()
report["groups"].append(run_group("B_framelabel", XB, YB, 3))
report["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}")
