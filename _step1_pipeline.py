#!/usr/bin/env python3
"""Step 1: Run scanner -> dedup -> scorer, then generate curation prompt."""
import sys, os, time

# Strip proxy env vars (proxy is DOWN)
for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]

sys.path.insert(0, '/root/fine-grained/scripts')

print("=== Step 1a: Scanner ===")
from pipeline.scanner import run as run_scanner
t0 = time.time()
run_scanner()
print(f"Scanner done in {time.time()-t0:.1f}s")

print("\n=== Step 1b: Dedup ===")
from pipeline.dedup import run as run_dedup
t0 = time.time()
run_dedup()
print(f"Dedup done in {time.time()-t0:.1f}s")

print("\n=== Step 1c: Scorer ===")
from pipeline.scorer import run as run_scorer
t0 = time.time()
run_scorer()
print(f"Scorer done in {time.time()-t0:.1f}s")

print("\n=== Step 1d: Generate Curation Prompt ===")
from pipeline.curator import get_candidates, get_curation_prompt
candidates = get_candidates(limit=20)
print(f"Got {len(candidates)} candidates for curation")
prompt = get_curation_prompt(candidates, count=10)
with open('data/curation_prompt.txt', 'w') as f:
    f.write(prompt)
print(f"Saved curation_prompt.txt ({len(prompt)} chars)")
print("Step 1 DONE")
