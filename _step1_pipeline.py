#!/usr/bin/env python3
"""Step 1: Run scanner -> dedup -> scorer, then generate curation_prompt.txt"""
import sys, os

# Strip proxy env vars (proxy is DOWN on this machine)
for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]

# Set up sys.path so pipeline imports work
sys.path.insert(0, '/root/fine-grained/scripts')

print("=" * 60)
print("STEP 1: Pipeline Run (scanner -> dedup -> scorer)")
print("=" * 60)

# Phase 1: Scanner
print("\n>>> Phase 1: Scanner")
from pipeline.scanner import run as run_scanner
run_scanner()

# Phase 2: Dedup
print("\n>>> Phase 2: Dedup")
from pipeline.dedup import run as run_dedup
run_dedup()

# Phase 3: Scorer
print("\n>>> Phase 3: Scorer")
from pipeline.scorer import run as run_scorer
run_scorer()

# Phase 4: Generate curation prompt
print("\n>>> Phase 4: Generate curation_prompt.txt")
from pipeline.curator import get_candidates, get_curation_prompt
candidates = get_candidates(limit=20)
print(f"  Candidates fetched: {len(candidates)}")
if candidates:
    prompt = get_curation_prompt(candidates, count=10)
    with open('/root/fine-grained/data/curation_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"  curation_prompt.txt written ({len(prompt)} chars)")
else:
    print("  WARNING: No candidates found!")
    # Write empty prompt file so Step 2 doesn't fail
    with open('/root/fine-grained/data/curation_prompt.txt', 'w', encoding='utf-8') as f:
        f.write("NO_CANDIDATES")
    print("  Empty placeholder written.")

print("\n>>> STEP 1 COMPLETE <<<")
