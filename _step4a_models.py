#!/usr/bin/env python3
"""Step 4: Model tracking - get candidates and generate extraction prompt"""
import sys, os
for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]
sys.path.insert(0, '/root/fine-grained/scripts')

from pipeline.model_tracker import get_candidate_articles, get_extraction_prompt

articles = get_candidate_articles(20)
print(f"Candidate articles for model extraction: {len(articles)}")

if articles:
    prompt = get_extraction_prompt(articles)
    with open('/root/fine-grained/data/model_extraction_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"Prompt written: {len(prompt)} chars")
    for a in articles:
        print(f"  DB ID: {a['id']}, Source: {a.get('source_name', 'N/A')}, Title: {a.get('title', 'N/A')[:80]}")
else:
    print("No candidate articles for model extraction.")
    with open('/root/fine-grained/data/model_extraction_prompt.txt', 'w') as f:
        f.write("NO_CANDIDATES")
