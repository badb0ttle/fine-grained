#!/usr/bin/env python3
"""Step 2: Apply curation to DB"""
import sys, os, json
for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]
sys.path.insert(0, '/root/fine-grained/scripts')

with open('/root/fine-grained/data/curated.json', 'r', encoding='utf-8') as f:
    curated = json.load(f)

from pipeline.curator import apply_curation
result = apply_curation(curated)
print(f"apply_curation result: {result}")
print("STEP 2 COMPLETE: Curation applied to DB")
