#!/usr/bin/env python3
"""Predict vGRF from 3D pose sequences and subject mass."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


class PoseDataset(Dataset):
    def __init__(self, poses_path, meta_path):
        self.poses = np.load(poses_path)  # (N, T, J, 3)
        meta = json.loads(Path(meta_path).read_text())
        self.mass = np.array(meta["mass"])  # (N,)
        self.vgrf = np.array(meta["vgrf"])  # (N, T)

    def __len__(self):
        return len(self.poses)

    def __getitem__(self, idx):
        return (
            torch.from_numpy(self.poses[idx]).float(),
            torch.tensor(self.mass[idx]).float(),
            torch.from_numpy(self.vgrf[idx]).float(),
        )


class SimpleTCN(nn.Module):
    def __init__(self, in_dim=51, hidden=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_dim, hidden, 3, padding=1),
            nn.ReLU(),
            nn.Conv1d(hidden, hidden, 3, padding=1),
            nn.ReLU(),
            nn.Conv1d(hidden, 1, 1),
        )

    def forward(self, x):
        # x: (B, T, J, 3)
        b, t, j, c = x.shape
        x = x.reshape(b, t, j * c).transpose(1, 2)
        y = self.net(x).transpose(1, 2)
        return y.squeeze(-1)


def physics_consistency(pred, poses, mass):
    # Simple vertical acceleration consistency: m * a_y ~ vGRF
    # approximate a_y from hip joint
    hip = poses[:, :, 11, 1]  # left hip y
    vel = hip[:, 1:] - hip[:, :-1]
    acc = vel[:, 1:] - vel[:, :-1]
    acc = torch.nn.functional.pad(acc, (0, 1))
    return torch.mean((pred - mass.unsqueeze(1) * acc) ** 2)


def train(args):
    ds = PoseDataset(args.poses, args.meta)
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SimpleTCN().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)

    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for poses, mass, vgrf in dl:
            poses, mass, vgrf = poses.to(device), mass.to(device), vgrf.to(device)
            pred = model(poses)
            loss = torch.mean((pred - vgrf) ** 2) + args.phys_weight * physics_consistency(pred, poses, mass)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += loss.item()
        print(f"Epoch {epoch}: loss={total / max(1, len(dl)):.4f}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "args": vars(args)}, out)


def predict_dynamics(model_path, poses, mass):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SimpleTCN().to(device)
    ckpt = torch.load(model_path, map_location=device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    with torch.no_grad():
        p = torch.from_numpy(poses).float().to(device)
        pred = model(p).cpu().numpy()
    return pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poses", default="./data/poses.npy")
    ap.add_argument("--meta", default="./data/meta.json")
    ap.add_argument("--out", default="./checkpoints/dynamics.pt")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--phys_weight", type=float, default=0.1)
    args = ap.parse_args()

    train(args)


if __name__ == "__main__":
    main()
