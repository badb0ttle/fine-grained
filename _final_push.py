#!/usr/bin/env python3
"""Final git push: add all, commit, pull rebase, push"""
import subprocess, sys

token = open('.git_token').read().strip()
url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"

# Step 1: git add -A
print("git add -A...")
subprocess.run(["git", "add", "-A"], cwd=".", check=True)

# Step 2: git commit (may fail if nothing to commit - that's OK)
print("git commit...")
r = subprocess.run(["git", "commit", "-m", "AI intel daily scan 2026-06-14"], cwd=".", capture_output=True, text=True)
print(r.stdout.strip())
if r.returncode != 0:
    if "nothing to commit" not in r.stdout and "nothing to commit" not in r.stderr:
        print(f"Commit warning: {r.stderr.strip()}")
    else:
        print("Nothing new to commit")

# Step 3: git pull --rebase
print("git pull --rebase...")
r = subprocess.run(["git", "pull", "--rebase", url, "main"], cwd=".", capture_output=True, text=True, timeout=60)
print(r.stdout.strip())
if r.returncode != 0:
    print(f"Pull error: {r.stderr.strip()}")

# Step 4: git push
print("git push...")
r = subprocess.run(["git", "push", url, "main"], cwd=".", capture_output=True, text=True, timeout=120)
print(r.stdout.strip())
print(r.stderr.strip())
if r.returncode == 0:
    print("\n✅ Final push successful!")
else:
    print(f"\n❌ Push failed with code {r.returncode}")
    sys.exit(r.returncode)
