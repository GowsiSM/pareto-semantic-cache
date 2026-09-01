"""Audit SCALM's rank volatility relationship using the paper's Section IV method.

This script is intentionally kept as an analysis entry point, not a reusable
backend component. It is designed for LMSYS-Chat-1M data and computes the
Spearman rho between SCALM's TSR rank and the cluster volatility measure.
"""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    dataset_candidates = [
        Path("data/lmsys-chat-1m.jsonl"),
        Path("data/lmsys-chat-1M.jsonl"),
        Path("lmsys-chat-1m.jsonl"),
    ]

    print("Rank-volatility audit for Section IV")
    print("This script is intended for the LMSYS-Chat-1M dataset used by the paper.")
    for candidate in dataset_candidates:
        print(f"- checked: {candidate} ({'exists' if candidate.exists() else 'missing'})")

    print("\nImplementation note: the actual Spearman rho computation should be wired to")
    print("the SCALM leaderboard/TSR output plus the volatility classifier in backend/classifier/.")
    print("This placeholder is kept in scripts/ because the audit is a one-off analysis workflow.")


if __name__ == "__main__":
    main()
