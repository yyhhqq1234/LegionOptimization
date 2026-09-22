"""Surrogate f(s,a)->(perf,power,temp): MLP 64-64-32+LN + 5-ensemble (torch)."""
import torch
import torch.nn as nn


class MLP(nn.Module):
    def __init__(self, in_dim=8, out_dim=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64), nn.LayerNorm(64), nn.ReLU(),
            nn.Linear(64, 64), nn.LayerNorm(64), nn.ReLU(),
            nn.Linear(64, 32), nn.LayerNorm(32), nn.ReLU(),
            nn.Linear(32, out_dim),
        )

    def forward(self, x):
        return self.net(x)


class Ensemble5(nn.Module):
    def __init__(self, in_dim=8, out_dim=3):
        super().__init__()
        self.members = nn.ModuleList([MLP(in_dim, out_dim) for _ in range(5)])

    def forward(self, x):
        outs = torch.stack([m(x) for m in self.members], dim=0)
        return outs.mean(0), outs.var(0).mean(-1)


def rank_loss(pred, target):
    """Pairwise RankLoss (approx): mean hinge on pairwise order."""
    n = pred.shape[0]
    if n < 2:
        return torch.tensor(0.0, device=pred.device)
    i = torch.randint(0, n, (min(256, n),), device=pred.device)
    j = torch.randint(0, n, (min(256, n),), device=pred.device)
    s = torch.sign(target[i] - target[j])
    m = -(pred[i] - pred[j]) * s
    return torch.clamp(m + 0.1, min=0.0).mean()


def monotonic_penalty(model, device="cpu"):
    """Physical monotonicity: d perf/d freq >=0 via finite diff on probe batch."""
    model.eval()
    base = torch.tensor([[40.0, 4.8, 50.0, 50.0, 0.0, 0.0, 0.0, 0.0]] * 16, device=device)
    base.requires_grad_(True)
    with torch.enable_grad():
        out = model(base) if not isinstance(model, Ensemble5) else model(base)[0]
        perf = out[:, 0].sum()
        g = torch.autograd.grad(perf, base, create_graph=True)[0][:, 1]
    viol = torch.clamp(-g, min=0.0).mean()
    model.train()
    return viol
