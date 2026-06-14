#!/usr/bin/env python3
"""Step 5: Clean up temp files and git push."""
import subprocess, os, sys

os.chdir('/root/fine-grained')

# Clean up temp files from Step 1
for f in ['_step1_data.py', 'data/weekly_prompt_cn.txt', 'data/weekly_prompt_en.txt', 'data/weekly_data.json']:
    path = os.path.join('/root/fine-grained', f)
    if os.path.exists(path):
        os.remove(path)
        print(f"Cleaned: {f}")

# Read token
token = open('.git_token').read().strip()
url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"

# Git add
result = subprocess.run(["git", "add", "-A"], cwd="/root/fine-grained", capture_output=True, text=True)
print(f"git add: {result.returncode}")

# Git commit
result = subprocess.run(
    ["git", "commit", "-m", "AI intel weekly briefing 2026-06-14"],
    cwd="/root/fine-grained", capture_output=True, text=True
)
print(f"git commit: {result.returncode}")
print(result.stdout.strip())
if result.stderr.strip():
    print(f"STDERR: {result.stderr.strip()}")

# Git pull --rebase
result = subprocess.run(
    ["git", "pull", "--rebase", url, "main"],
    cwd="/root/fine-grained", capture_output=True, text=True, timeout=60
)
print(f"git pull --rebase: {result.returncode}")
print(result.stdout.strip())
if result.stderr.strip():
    print(f"STDERR: {result.stderr.strip()}")

# Git push
result = subprocess.run(
    ["git", "push", url, "main"],
    cwd="/root/fine-grained", capture_output=True, text=True, timeout=120
)
print(f"git push: {result.returncode}")
print(result.stdout.strip())
if result.stderr.strip():
    print(f"STDERR: {result.stderr.strip()}")

print("Step 5 complete.")
