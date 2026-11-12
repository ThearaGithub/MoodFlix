"""Train the latent-factor model and print its held-out metrics.

Usage: python scripts/evaluate_model.py

This is the same model the app trains on startup (see src/model.py); the
script exists so the numbers can be reproduced outside Streamlit, for the
project report.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import load_ratings  # noqa: E402
from src.model import train  # noqa: E402


def main() -> None:
    ratings = load_ratings()
    started = time.time()
    model = train(ratings)
    metrics = model["metrics"]

    print(f"Trained in {time.time() - started:.2f}s on {len(ratings):,} ratings")
    print(f"Split: {metrics['train_ratings']:,} train / "
          f"{metrics['test_ratings']:,} test (per-user holdout)")
    print(f"Users: {metrics['users']} · Movies: {metrics['items']:,} · "
          f"Factors: {metrics['factors']}")
    print()
    print("Rating prediction (lower is better)")
    print(f"  Global mean baseline : RMSE {metrics['rmse_baseline']:.4f}")
    print(f"  Item+user biases     : RMSE {metrics['rmse_item_bias']:.4f}")
    print(f"  SVD model            : RMSE {metrics['rmse_model']:.4f} · "
          f"MAE {metrics['mae_model']:.4f}")
    print()
    print(f"Ranking (precision@{metrics['k']}, higher is better)")
    print(f"  Popularity           : {metrics['precision_popularity']:.4f}")
    print(f"  Quality prior        : {metrics['precision_quality']:.4f}")
    print(f"  Model + quality      : {metrics['precision_model']:.4f}")

    out = ROOT / "data" / "model_metrics.json"
    out.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"\nMetrics written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
