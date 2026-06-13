#!/usr/bin/env python3
"""Apply LLM analysis results (paper + model) to database."""
import sys, os, json

for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]

sys.path.insert(0, '/root/fine-grained/scripts')

# === Apply Paper Analysis ===
print("=== Apply Paper Analysis ===")
from pipeline.paper_analyzer import apply_analysis
papers = json.load(open('data/paper_analysis.json'))
apply_analysis(papers)
print(f"Applied analysis for {len(papers)} papers")

# === Apply Model Extraction ===
print("\n=== Apply Model Extraction ===")
from pipeline.model_tracker import apply_models
models = json.load(open('data/model_extraction.json'))
apply_models(models)
print(f"Applied {len(models)} models")

print("LLM analysis applied DONE")
