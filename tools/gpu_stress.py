"""GPU synthetic load: torch matmul loop, bounded time, read-only compute (no system writes).

Honest provenance: rows logged by collect_shadow with --work STRESS to a
D_stress_* file (NOT D_safe_*), excluded from 9-grid coverage. Real grid
cells + plug events still require genuine usage and physical unplug.
"""
import argparse
import time

import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=180)
    ap.add_argument("--size", type=int, default=4096)
    args = ap.parse_args()
    assert torch.cuda.is_available(), "no CUDA, stress refused"
    a = torch.randn(args.size, args.size, device="cuda")
    b = torch.randn(args.size, args.size, device="cuda")
    t0 = time.time()
    n = 0
    while time.time() - t0 < args.seconds:
        c = a @ b
        c.mul_(1.0)
        torch.cuda.synchronize()
        n += 1
    print(f"stress done iters={n} secs={time.time() - t0:.0f} (pure compute, zero system writes)")


if __name__ == "__main__":
    main()
