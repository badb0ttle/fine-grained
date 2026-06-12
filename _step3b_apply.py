#!/usr/bin/env python3
"""Step 3b: Apply paper analysis to DB"""
import sys, os, json
for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]
sys.path.insert(0, '/root/fine-grained/scripts')

with open('/root/fine-grained/data/paper_analysis_results.json', 'r') as f:
    results = json.load(f)

from pipeline.paper_analyzer import apply_analysis
result = apply_analysis(results)
print(f"Paper analysis applied: {result}")
print("STEP 3 COMPLETE")
