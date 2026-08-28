import json
from pathlib import Path

import numpy as np


def generate_synthetic(out_dir="./data", n=50, t=60, j=17):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    poses = np.random.randn(n, t, j, 3).astype(np.float32) * 0.1
    mass = np.random.uniform(50, 90, size=(n,)).astype(np.float32)
    vgrf = np.random.randn(n, t).astype(np.float32) * 0.2

    np.save(out / "poses.npy", poses)
    meta = {"mass": mass.tolist(), "vgrf": vgrf.tolist()}
    (out / "meta.json").write_text(json.dumps(meta))


if __name__ == "__main__":
    generate_synthetic()
