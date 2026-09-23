# test_api.py
"""Test the backend API with the 2000-query experiment."""

import requests
import json
import time

API_URL = "http://127.0.0.1:8000/api/experiments/run"

# Your exact parameters
payload = {
    "dataset": "moss",
    "n_queries": 2000,
    "capacity": 100,
    "warmup_count": 100,
    "similarity_threshold": 0.9,
    "embedding": "sentence-transformer",
    "seed": 42
}

print("=" * 60)
print("Testing Backend API")
print("=" * 60)
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

start = time.time()
response = requests.post(API_URL, json=payload, timeout=3600)
elapsed = time.time() - start

print(f"Status: {response.status_code}")
print(f"Time: {elapsed:.1f} seconds")
print()

if response.status_code == 200:
    result = response.json()
    
    print("=" * 60)
    print("Results")
    print("=" * 60)
    
    for system, metrics in result["systems"].items():
        print(f"\n{system.upper()}:")
        print(f"  Hit Rate:          {metrics['hit_rate']:.2%}")
        print(f"  Token Savings:     {metrics['token_saving_rate']:.2%}")
        print(f"  Staleness Rate:    {metrics['staleness_rate']:.2%}")
        print(f"  False-Hit Rate:    {metrics['false_hit_rate']:.2%}")
        print(f"  Hits / Misses:     {metrics['hits']} / {metrics['misses']}")
    
    print(f"\nMetadata:")
    print(f"  Embedding Model:   {result['meta']['embedding_model']}")
    print(f"  Duration:          {result['meta']['duration_ms']:.0f} ms")
    print(f"  Dataset Size:      {result['meta']['dataset_size']}")
else:
    print(f"Error: {response.text}")