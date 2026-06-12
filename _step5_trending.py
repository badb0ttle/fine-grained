#!/usr/bin/env python3
"""Step 5: GitHub Trending + Paper-Code Linking"""
import sys, os
from pathlib import Path

for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]

sys.path.insert(0, '/root/fine-grained/scripts')

token = Path('/root/fine-grained/.git_token').read_text().strip()

# Part A: GitHub Trending
print("=" * 60)
print("STEP 5A: GitHub Trending")
print("=" * 60)
try:
    from pipeline.github_trending import run as run_trending
    result = run_trending()
    print(f"GitHub Trending result: {result}")
except Exception as e:
    print(f"GitHub Trending error: {e}")

# Part B: Paper-Code Linking
print("\n" + "=" * 60)
print("STEP 5B: Paper-Code Linking")
print("=" * 60)
try:
    from pipeline.paper_code_link import run as run_code_link
    result = run_code_link(limit=5, token=token)
    print(f"Paper-Code Link result: {result}")
except Exception as e:
    print(f"Paper-Code Link error: {e}")

print("\nSTEP 5 COMPLETE")
