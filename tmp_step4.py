import json, sys
sys.path.insert(0, '/Users/mac/Desktop/Projects/ai-intel')
from scripts.pipeline.curator import apply_curation

with open('data/curated.json') as f:
    curated = json.load(f)

result = apply_curation(curated)
print(f"Applied curation: {result}")
