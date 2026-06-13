#!/usr/bin/env python3
"""Step 6: Run publisher, then push remaining files."""
import sys, os, json, subprocess, time

for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]

sys.path.insert(0, '/root/fine-grained/scripts')

# === Run Publisher ===
print("=== Publisher ===")
from pipeline.publisher import run as run_publisher
run_publisher()
print("Publisher DONE")

# === Push remaining files ===
print("\n=== Push Remaining Files ===")
token = open('.git_token').read().strip()
url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"

# 1. git add -A + commit
subprocess.run(["git", "add", "-A"], cwd="/root/fine-grained", check=True)
result = subprocess.run(
    ["git", "commit", "-m", "AI intel daily scan 2026-06-13"],
    cwd="/root/fine-grained", capture_output=True, text=True
)
print(f"Commit: {result.stdout.strip()}")
if result.stderr:
    print(f"Stderr: {result.stderr.strip()}")

# 2. git pull --rebase
print("Pulling with rebase...")
result = subprocess.run(
    ["git", "pull", "--rebase", url, "main"],
    cwd="/root/fine-grained", capture_output=True, text=True, timeout=60
)
print(f"Pull: {result.stdout.strip()}")
if result.stderr:
    print(f"Stderr: {result.stderr.strip()}")

# 3. git push
print("Pushing...")
result = subprocess.run(
    ["git", "push", url, "main"],
    cwd="/root/fine-grained", capture_output=True, text=True, timeout=120
)
print(f"Push: {result.stdout.strip()}")
if result.stderr and "Everything up-to-date" not in result.stderr:
    print(f"Stderr: {result.stderr.strip()}")

print("Push DONE")
print("Step 6 COMPLETE")
