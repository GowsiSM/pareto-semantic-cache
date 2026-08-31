# test_loader.py
"""
Test the MOSS loader with the sample file.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.experiment.moss_loader import MOSSLoader


def safe_preview(value: str, max_chars: int = 200) -> str:
    preview = str(value)[:max_chars]
    return preview.encode("ascii", errors="replace").decode("ascii")


def resolve_dataset_path() -> Path:
    candidates = [
        PROJECT_ROOT / "data" / "moss-sample-10k.jsonl",
        PROJECT_ROOT / "moss-sample-10k.jsonl",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def main():
    print("Testing MOSS Loader")
    print("=" * 60)

    dataset_path = resolve_dataset_path()
    print(f"Using dataset: {dataset_path}")
    loader = MOSSLoader(str(dataset_path))
    print(f"\nLoaded {len(loader)} conversations")
    
    # Get stats
    stats = loader.get_stats()
    print(f"\nDataset stats:")
    print(f"   Total conversations: {stats['total_conversations']:,}")
    print(f"   Total turns: {stats['total_turns']:,}")
    print(f"   Avg turns per conversation: {stats['avg_turns_per_conversation']:.1f}")
    print(f"   Categories: {stats['categories']}")
    
    # Get first-turn pairs
    pairs = loader.get_first_turn_pairs()
    print(f"\nExtracted {len(pairs)} first-turn QA pairs")
    
    if pairs:
        print("\nSample QA pairs (first 3):")
        for i, (q, a) in enumerate(pairs[:3]):
            print(f"\nPair {i+1}:")
            print(f"  Q: {safe_preview(q, 200)}...")
            print(f"  A: {safe_preview(a, 200)}...")
    else:
        print("\nNo QA pairs extracted!")

if __name__ == "__main__":
    main()