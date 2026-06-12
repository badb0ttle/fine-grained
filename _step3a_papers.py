#!/usr/bin/env python3
"""Step 3: Paper analysis - get unanalyzed papers and generate prompt"""
import sys, os
for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]
sys.path.insert(0, '/root/fine-grained/scripts')

from pipeline.paper_analyzer import get_unanalyzed_papers, get_analysis_prompt

papers = get_unanalyzed_papers(10)
print(f"Unanalyzed papers: {len(papers)}")

if papers:
    prompt = get_analysis_prompt(papers)
    with open('/root/fine-grained/data/paper_analysis_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"Prompt written: {len(prompt)} chars")
    # Also print the paper IDs for reference
    for p in papers:
        print(f"  Paper DB ID: {p['id']}, arXiv: {p.get('paper_id', 'N/A')}, Title: {p.get('title', 'N/A')[:80]}")
else:
    print("No unanalyzed papers found.")
    with open('/root/fine-grained/data/paper_analysis_prompt.txt', 'w') as f:
        f.write("NO_PAPERS")
