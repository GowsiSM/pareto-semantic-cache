# test_loader.py
"""
Test the MOSS loader with the sample file.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from backend.experiment.moss_loader import MOSSLoader

def main():
    print("Testing MOSS Loader")
    print("=" * 60)
    
    loader = MOSSLoader("moss-sample-10k.jsonl")
    print(f"\n✅ Loaded {len(loader)} conversations")
    
    # Get stats
    stats = loader.get_stats()
    print(f"\n📊 Dataset stats:")
    print(f"   Total conversations: {stats['total_conversations']:,}")
    print(f"   Total turns: {stats['total_turns']:,}")
    print(f"   Avg turns per conversation: {stats['avg_turns_per_conversation']:.1f}")
    print(f"   Categories: {stats['categories']}")
    
    # Get first-turn pairs
    pairs = loader.get_first_turn_pairs()
    print(f"\n✅ Extracted {len(pairs)} first-turn QA pairs")
    
    if pairs:
        print("\n📖 Sample QA pairs (first 3):")
        for i, (q, a) in enumerate(pairs[:3]):
            print(f"\nPair {i+1}:")
            print(f"  Q: {q[:200]}...")
            print(f"  A: {a[:200]}...")
    else:
        print("\n❌ No QA pairs extracted!")

if __name__ == "__main__":
    main()