#!/usr/bin/env python3
"""Deploy: scan RSS sources, generate site data, and push to GitHub Pages."""

import subprocess
import sys
import os
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
TOKEN_FILE = REPO_DIR / ".git_token"


def run(cmd, cwd=None):
    print(f"→ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or REPO_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠️  {result.stderr.strip()}")
    else:
        print(f"  ✅ {result.stdout.strip()[:100]}")
    return result.returncode == 0


def main():
    os.chdir(REPO_DIR)

    # Step 1: Read token
    if not TOKEN_FILE.exists():
        print("❌ .git_token not found. Run setup first.")
        sys.exit(1)
    token = TOKEN_FILE.read_text().strip()

    # Step 2: Pull latest (avoid conflicts)
    run(["git", "pull", "origin", "main", "--rebase"])

    # Step 3: Run RSS scanner
    print("\n📡 Scanning RSS sources...")
    result = subprocess.run(
        [sys.executable, "scripts/rss_scanner.py"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Scanner failed: {result.stderr}")
        sys.exit(1)

    # Step 4: Commit and push
    print("\n📤 Pushing to GitHub...")
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", "📡 Daily AI intel scan"])
    
    push_url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"
    result = subprocess.run(
        ["git", "push", push_url, "main"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    if result.returncode == 0:
        print(f"\n🎉 Deployed! → https://ai.hjhai.xyz")
    else:
        # Check if nothing to commit
        if "nothing to commit" in result.stdout or "everything up-to-date" in result.stderr:
            print("✅ Already up to date.")
        else:
            print(f"⚠️  Push issue: {result.stderr}")


if __name__ == "__main__":
    main()
