#!/usr/bin/env python3
"""Step 6: Publisher + Git Push + Telegram Digest"""
import sys, os, subprocess, json
from pathlib import Path
from datetime import datetime

for key in list(os.environ.keys()):
    if key.lower().endswith('_proxy'):
        del os.environ[key]

sys.path.insert(0, '/root/fine-grained/scripts')

WORKDIR = '/root/fine-grained'
token = Path(f'{WORKDIR}/.git_token').read_text().strip()
url = f'https://oauth2:{token}@github.com/badb0ttle/fine-grained.git'
today_str = datetime.now().strftime('%Y-%m-%d')

# Part A: Publisher
print("=" * 60)
print("STEP 6A: Publisher")
print("=" * 60)
try:
    from pipeline.publisher import run as run_publisher
    result = run_publisher()
    print(f"Publisher result: {result}")
except Exception as e:
    print(f"Publisher error: {e}")

# Part B: Git pull --rebase + add + commit + push
print("\n" + "=" * 60)
print("STEP 6B: Git Pull + Push")
print("=" * 60)
os.chdir(WORKDIR)

# Pull rebase first to avoid non-fast-forward
print(">>> git pull --rebase")
r = subprocess.run(["git", "pull", "--rebase", url, "main"], cwd=WORKDIR,
                   capture_output=True, text=True, timeout=60)
print(f"  stdout: {r.stdout.strip()}")
if r.stderr.strip():
    print(f"  stderr: {r.stderr.strip()}")

# Add everything
print(">>> git add -A")
r = subprocess.run(["git", "add", "-A"], cwd=WORKDIR,
                   capture_output=True, text=True, timeout=30)
print(f"  exit: {r.returncode}")

# Commit (no emoji per skill rule)
commit_msg = f"AI intel daily scan {today_str}"
print(f">>> git commit -m '{commit_msg}'")
r = subprocess.run(["git", "commit", "-m", commit_msg], cwd=WORKDIR,
                   capture_output=True, text=True, timeout=30)
print(f"  stdout: {r.stdout.strip()}")
if r.stderr.strip():
    print(f"  stderr: {r.stderr.strip()}")

# Push
print(">>> git push")
r = subprocess.run(["git", "push", url, "main"], cwd=WORKDIR,
                   capture_output=True, text=True, timeout=120)
print(f"  stdout: {r.stdout.strip()}")
if r.stderr.strip():
    print(f"  stderr: {r.stderr.strip()}")
print(f"  exit: {r.returncode}")

# Part C: Telegram Digest (for final output)
print("\n" + "=" * 60)
print("STEP 6C: Telegram Digest")
print("=" * 60)
try:
    from pipeline.telegram_digest import format_digest
    digest = format_digest()
    with open(f'{WORKDIR}/data/telegram_digest.txt', 'w', encoding='utf-8') as f:
        f.write(digest)
    print(f"Digest written: {len(digest)} chars")
    print("\n--- DIGEST PREVIEW (first 500 chars) ---")
    print(digest[:500])
except Exception as e:
    print(f"Telegram digest error: {e}")
    digest = f"AI 情报站每日扫描完成 - {today_str}"

print("\nSTEP 6 COMPLETE")
print("DIGEST_START")
print(digest)
print("DIGEST_END")
