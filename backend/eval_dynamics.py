#!/usr/bin/env python3
"""Evaluate vGRF prediction correlation."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from train_dynamics import SimpleTCN


def corr(a, b):
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum()) * np.sqrt((b * b).sum()) + 1e-8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poses", default="./data/poses.npy")
    ap.add_argument("--meta", default="./data/meta.json")
    ap.add_argument("--model", default="./checkpoints/dynamics.pt")
    args = ap.parse_args()

    poses = np.load(args.poses)
    meta = json.loads(Path(args.meta).read_text())
    vgrf = np.array(meta["vgrf"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SimpleTCN().to(device)
    ckpt = torch.load(args.model, map_location=device)
    model.load_state_dict(ckpt["model"])
    model.eval()

    with torch.no_grad():
        pred = model(torch.from_numpy(poses).float().to(device)).cpu().numpy()

    # average correlation across samples
    c = [corr(pred[i], vgrf[i]) for i in range(len(pred))]
    print("Mean correlation:", sum(c) / len(c))


if __name__ == "__main__":
    main()
