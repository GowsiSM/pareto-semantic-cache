# run.py
"""
Run SCALM validation on the MOSS dataset.
Uses the 10k sample extracted from the full dataset.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from backend.experiment.moss_loader import MOSSLoader
from backend.experiment.scalm_validator import SCALMValidator

DATASET_PATH = "moss-sample-10k.jsonl"

if not os.path.exists(DATASET_PATH):
    print(f"❌ Sample file not found: {DATASET_PATH}")
    print("   Please run: python extract_sample.py")
    sys.exit(1)

SAMPLE_SIZE = 5000
CACHE_CAPACITY = 100
SIMILARITY_THRESHOLD = 0.90
WARMUP_COUNT = 100

SEPARATOR = "=" * 60

def print_section(title: str) -> None:
    print(SEPARATOR)
    print(title)
    print(SEPARATOR)

def main() -> None:
    print_section("SCALM Validation on MOSS Dataset")
    
    # Load dataset
    print(f"📂 Loading dataset from: {DATASET_PATH}")
    loader = MOSSLoader(DATASET_PATH)
    print(f"✅ Loaded {len(loader)} conversations")
    
    # Show dataset stats
    stats = loader.get_stats()
    print(f"📊 Dataset stats:")
    print(f"   Total conversations: {stats['total_conversations']:,}")
    print(f"   Total turns: {stats['total_turns']:,}")
    print(f"   Avg turns per conversation: {stats['avg_turns_per_conversation']:.1f}")
    print(f"   Categories: {stats['categories']}")

    # Extract first-turn QA pairs
    qa_pairs = loader.get_first_turn_pairs()
    print(f"✅ Extracted {len(qa_pairs)} first-turn QA pairs")
    
    # Limit to sample size
    qa_pairs = qa_pairs[:SAMPLE_SIZE]
    print(f"✅ Using {len(qa_pairs)} samples for validation")

    if len(qa_pairs) == 0:
        print("❌ No QA pairs extracted! Check the loader.")
        return

    # Show sample pairs
    print("\n📖 Sample QA pairs:")
    for i, (q, a) in enumerate(qa_pairs[:2]):
        print(f"\nPair {i+1}:")
        print(f"  Q: {q[:150]}...")
        print(f"  A: {a[:150]}...")

    # Run SCALM validation
    print("\n🔬 Running SCALM validation...")
    print("   (This may take a few minutes for embeddings generation)")
    
    validator = SCALMValidator(
        capacity=CACHE_CAPACITY,
        similarity_threshold=SIMILARITY_THRESHOLD,
    )
    results = validator.run(qa_pairs, warmup_count=WARMUP_COUNT)

    # Display results
    print()
    print_section("📊 SCALM Validation Results")
    print(f"Total Queries:        {results['total_queries']:,}")
    print(f"Cache Hits:           {results['hits']:,}")
    print(f"Cache Misses:         {results['misses']:,}")
    print(f"LLM Calls Avoided:    {results['llm_calls']:,}")
    print()
    print("📈 Metrics:")
    print(f"Cache Hit Rate:       {results['hit_rate']:.2%}")
    print(f"Token Saving Rate:    {results['token_saving_rate']:.2%}")
    print(f"Tokens Saved:         {results['tokens_saved']:,}")
    print(f"Total Tokens:         {results['total_tokens']:,}")

    # Compare with paper
    print()
    print_section("📖 Comparison with SCALM Paper")
    print("Paper's Reported Hit Rate:      ~63% improvement over GPTCache")
    print("Paper's Reported Token Savings: ~77% improvement over GPTCache")
    print()
    print(f"Your Hit Rate:                  {results['hit_rate']:.2%}")
    print(f"Your Token Saving Rate:         {results['token_saving_rate']:.2%}")

    # Interpretation
    print()
    print_section("💡 Interpretation")
    if results["hit_rate"] > 0.10:
        print("✅ Your results are in the expected range.")
        print("   The SCALM paper reports improvements over GPTCache,")
        print("   not absolute hit rates. Your hit rate of")
        print(f"   {results['hit_rate']:.2%} is reasonable for a semantic cache.")
    else:
        print("⚠️ Your hit rate is lower than expected.")
        print("   This could be due to:")
        print("   - Different dataset subset (you used MOSS, paper used LMSYS)")
        print("   - Different similarity threshold")
        print("   - Pattern ranking not yet implemented (TSR)")
        print("   - TSR-based admission not yet implemented")
        print()
        print("   Next steps:")
        print("   1. Implement TSR (Token Saving Ratio) ranking")
        print("   2. Implement pattern ranking (HIGH/MID/LOW)")
        print("   3. Re-run validation")

if __name__ == "__main__":
    main()