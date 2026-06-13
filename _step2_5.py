#!/usr/bin/env python3
"""Step 2-5: Apply curation, paper analysis, model tracking, github trending, paper-code links."""
import sys, os, json, time

# Strip proxy env vars
for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]

sys.path.insert(0, '/root/fine-grained/scripts')

results = {}

# === Step 2: Apply Curation ===
print("=== Step 2: Apply Curation ===")
from pipeline.curator import apply_curation
curated = json.load(open('data/curated.json'))
apply_curation(curated)
print(f"Applied curation for {len(curated)} articles")
results['curation'] = f"{len(curated)} applied"

# === Step 3: Paper Analysis ===
print("\n=== Step 3: Paper Analysis ===")
from pipeline.paper_analyzer import get_unanalyzed_papers, get_analysis_prompt, apply_analysis
papers = get_unanalyzed_papers(10)
print(f"Got {len(papers)} unanalyzed papers")
results['paper_analysis'] = f"{len(papers)} candidates"

if papers:
    prompt = get_analysis_prompt(papers)
    with open('data/paper_analysis_prompt.txt', 'w') as f:
        f.write(prompt)
    print(f"Saved paper_analysis_prompt.txt ({len(prompt)} chars)")
    print("LLM analysis prompt ready (use python3 _step3b_llm_paper.py to run LLM)")
else:
    print("No unanalyzed papers found")

# === Step 4: Model Tracking ===
print("\n=== Step 4: Model Tracking ===")
from pipeline.model_tracker import get_candidate_articles, get_extraction_prompt, apply_models
articles = get_candidate_articles(20)
print(f"Got {len(articles)} candidate articles for model extraction")
results['model_tracking'] = f"{len(articles)} candidates"

if articles:
    prompt = get_extraction_prompt(articles)
    with open('data/model_extraction_prompt.txt', 'w') as f:
        f.write(prompt)
    print(f"Saved model_extraction_prompt.txt ({len(prompt)} chars)")
    print("LLM extraction prompt ready (use python3 _step4b_llm_model.py to run LLM)")
else:
    print("No candidate articles for model extraction")

# === Step 5a: GitHub Trending ===
print("\n=== Step 5a: GitHub Trending ===")
from pipeline.github_trending import run as run_trending
run_trending()
print("GitHub Trending done")
results['github_trending'] = "done"

# === Step 5b: Paper-Code Linking ===
print("\n=== Step 5b: Paper-Code Linking ===")
from pipeline.paper_code_link import run as run_paper_code_link
token = open('.git_token').read().strip()
result = run_paper_code_link(limit=5, token=token)
print(f"Paper-code linking: {result}")
results['paper_code_link'] = str(result)

print("\n=== Steps 2-5 Summary ===")
print(json.dumps(results, ensure_ascii=False, indent=2))
print("Steps 2-5 DONE")
