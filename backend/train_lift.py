#!/usr/bin/env python3
"""Train a 2D-to-3D lifting model (TCN or Transformer)."""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.utils.tensorboard import SummaryWriter


def mpjpe(pred, gt):
    return torch.mean(torch.norm(pred - gt, dim=-1))


def bone_length_loss(pred):
    # Simple bone length regularizer for COCO-17 like skeleton
    bones = [
        (5, 7), (7, 9),  # left arm
        (6, 8), (8, 10),  # right arm
        (11, 13), (13, 15),  # left leg
        (12, 14), (14, 16),  # right leg
        (5, 6), (5, 11), (6, 12), (11, 12),  # torso
    ]
    loss = 0.0
    for a, b in bones:
        loss = loss + torch.mean(torch.norm(pred[:, :, a] - pred[:, :, b], dim=-1))
    return loss / len(bones)


class KeypointDataset(Dataset):
    def __init__(self, npz_path):
        data = np.load(npz_path)
        self.x = data["x"]  # (N, T, 17, 2)
        self.y = data["y"]  # (N, T, 17, 3)

    def __len__(self):
        return len(self.x)

    def __getitem__(self, idx):
        return (
            torch.from_numpy(self.x[idx]).float(),
            torch.from_numpy(self.y[idx]).float(),
        )


class TCN(nn.Module):
    def __init__(self, in_dim=34, hidden=128, out_dim=51):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_dim, hidden, 3, padding=1),
            nn.ReLU(),
            nn.Conv1d(hidden, hidden, 3, padding=1),
            nn.ReLU(),
            nn.Conv1d(hidden, out_dim, 1),
        )

    def forward(self, x):
        # x: (B, T, 17, 2)
        b, t, j, c = x.shape
        x = x.reshape(b, t, j * c).transpose(1, 2)
        y = self.net(x).transpose(1, 2)
        return y.reshape(b, t, j, 3)


class SimpleTransformer(nn.Module):
    def __init__(self, in_dim=34, d_model=128, nhead=4, num_layers=2, out_dim=51):
        super().__init__()
        self.proj = nn.Linear(in_dim, d_model)
        enc_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, batch_first=True)
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
        self.out = nn.Linear(d_model, out_dim)

    def forward(self, x):
        b, t, j, c = x.shape
        x = x.reshape(b, t, j * c)
        x = self.proj(x)
        x = self.encoder(x)
        y = self.out(x)
        return y.reshape(b, t, j, 3)


def train(args):
    train_ds = KeypointDataset(args.train)
    val_ds = KeypointDataset(args.val)

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch)

    if args.model == "tcn":
        model = TCN()
    else:
        model = SimpleTransformer()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    optim = torch.optim.Adam(model.parameters(), lr=args.lr)
    writer = SummaryWriter(log_dir=args.logdir)

    best_val = 1e9
    patience = args.patience
    bad_epochs = 0

    for epoch in range(args.epochs):
        model.train()
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            pred = model(x)
            loss = torch.mean((pred - y) ** 2) + args.bone_weight * bone_length_loss(pred)
            optim.zero_grad()
            loss.backward()
            optim.step()

        model.eval()
        val_loss = 0.0
        val_mpjpe = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                pred = model(x)
                val_loss += torch.mean((pred - y) ** 2).item()
                val_mpjpe += mpjpe(pred, y).item()

        val_loss /= max(1, len(val_loader))
        val_mpjpe /= max(1, len(val_loader))
        writer.add_scalar("val/loss", val_loss, epoch)
        writer.add_scalar("val/mpjpe", val_mpjpe, epoch)

        if val_loss < best_val:
            best_val = val_loss
            bad_epochs = 0
            ckpt = Path(args.checkpoints) / f"best_{args.model}.pt"
            ckpt.parent.mkdir(parents=True, exist_ok=True)
            torch.save({"model": model.state_dict(), "args": vars(args)}, ckpt)
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                print("Early stopping")
                break

    writer.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True, help="./data/train.npz")
    ap.add_argument("--val", required=True, help="./data/val.npz")
    ap.add_argument("--model", choices=["tcn", "transformer"], default="tcn")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--bone_weight", type=float, default=0.01)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--checkpoints", default="./checkpoints")
    ap.add_argument("--logdir", default="./runs")
    args = ap.parse_args()

    train(args)


if __name__ == "__main__":
    main()
