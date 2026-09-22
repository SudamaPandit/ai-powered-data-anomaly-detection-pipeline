from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def generate_claims(rows: int, seed: int, anomaly: bool) -> pd.DataFrame:
    """Generate non-PHI claim-like data for development and repeatable tests."""
    rng = np.random.default_rng(seed)
    now = datetime.now(UTC).replace(microsecond=0)
    amounts = np.maximum(0, rng.lognormal(mean=5.25, sigma=0.65, size=rows)).round(2)
    frame = pd.DataFrame(
        {
            "claim_id": [f"CLM-{index:07d}" for index in range(rows)],
            "member_id": [f"MBR-{value:06d}" for value in rng.integers(1, 50_000, rows)],
            "provider_id": [f"PRV-{value:04d}" for value in rng.integers(1, 2_000, rows)],
            "service_date": [
                (now - timedelta(days=int(value))).date().isoformat()
                for value in rng.integers(1, 30, rows)
            ],
            "diagnosis_code": rng.choice(["I10", "E11.9", "J45.909", "M54.5"], rows),
            "claim_amount": amounts,
            "claim_status": rng.choice(
                ["APPROVED", "DENIED", "PENDING"], rows, p=[0.72, 0.12, 0.16]
            ),
            "source_system": "synthetic_partner",
            "ingested_at": [
                (now - timedelta(minutes=int(value))).isoformat()
                for value in rng.integers(0, 90, rows)
            ],
        }
    )
    if anomaly and rows >= 20:
        frame.loc[: max(1, rows // 20), "member_id"] = None
        frame.loc[rows // 4, "claim_amount"] = -100.0
        frame.loc[rows // 3, "claim_status"] = "UNMAPPED"
        frame.loc[rows // 2, "claim_amount"] = frame["claim_amount"].median() * 50
        frame.loc[rows - 1, "claim_id"] = frame.loc[rows - 2, "claim_id"]
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--anomaly", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("--rows must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_claims(args.rows, args.seed, args.anomaly).to_csv(args.output, index=False)
    print(f"Wrote {args.rows} synthetic rows to {args.output}")


if __name__ == "__main__":
    main()
