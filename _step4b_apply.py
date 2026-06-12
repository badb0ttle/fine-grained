#!/usr/bin/env python3
"""Step 4b: Apply model extraction to DB"""
import sys, os, json
for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]
sys.path.insert(0, '/root/fine-grained/scripts')

with open('/root/fine-grained/data/model_extraction_results.json', 'r') as f:
    results = json.load(f)

from pipeline.model_tracker import apply_models
result = apply_models(results)
print(f"Model extraction applied: {result}")
print("STEP 4 COMPLETE")
