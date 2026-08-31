# extract_sample.py
"""
Extract a subset of MOSS dataset for SCALM validation.
This avoids loading the entire 11GB file.
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

INPUT_CANDIDATES = [
    DATA_DIR / "moss-003-sft-no-tools.jsonl",
    PROJECT_ROOT / "moss-003-sft-no-tools.jsonl",
]
OUTPUT_FILE = DATA_DIR / "moss-sample-10k.jsonl"
NUM_LINES = 10000  # SCALM paper uses ~10k conversations

INPUT_FILE = next((path for path in INPUT_CANDIDATES if path.exists()), INPUT_CANDIDATES[0])

def extract_sample(input_path, output_path, num_lines):
    """Extract first N lines from JSONL file."""
    print(f"Reading from: {input_path}")
    print(f"Extracting {num_lines:,} lines")
    
    # Get file size
    size = os.path.getsize(input_path)
    size_gb = size / (1024**3)
    print(f"File size: {size_gb:.2f} GB")
    
    count = 0
    with open(input_path, 'r', encoding='utf-8') as f_in:
        with open(output_path, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                if count >= num_lines:
                    break
                # Write line as-is (no JSON parsing for speed)
                f_out.write(line)
                count += 1
                
                if count % 1000 == 0:
                    print(f"   Extracted {count:,} lines...")
    
    print(f"Extracted {count:,} lines to: {output_path}")
    
    # Show first line structure
    print("\nSample structure (first line):")
    with open(output_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        try:
            data = json.loads(first_line)
            print(json.dumps(data, indent=2)[:500] + "...")
        except:
            print("Could not parse first line")

if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        print("   Make sure moss-003-sft-no-tools.jsonl is present under data/ or the project root")
    else:
        extract_sample(INPUT_FILE, OUTPUT_FILE, NUM_LINES)