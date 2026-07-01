#!/usr/bin/env python3
"""
部署脚本 (Deploy)
=================
自动化部署流程：扫描 RSS 信源 → 生成站点数据 → 推送到 GitHub Pages。

完整的 CI/CD 替代方案，适用于 cron 触发的一键部署。

流程：
1. 读取 .git_token（GitHub Personal Access Token）
2. git pull --rebase（拉取最新代码，避免冲突）
3. 运行 rss_scanner.py（采集最新文章）
4. git add -A + git commit + git push（推送所有变更）
5. GitHub Pages 自动构建部署 → https://ai.hjhai.xyz

注意事项：
- .git_token 文件必须存在且包含有效的 GitHub PAT
- 推送使用 OAuth2 token 认证（HTTPS URL 中嵌入 token）
"""

import subprocess
import sys
import os
from pathlib import Path

# 项目根目录
REPO_DIR = Path(__file__).parent.parent
TOKEN_FILE = REPO_DIR / ".git_token"


def run(cmd, cwd=None):
    """
    执行 shell 命令并打印结果。

    Args:
        cmd: 命令及其参数列表（如 ["git", "pull"]）。
        cwd: 工作目录，默认为项目根目录。

    Returns:
        bool: True 表示命令成功（returncode == 0）。
    """
    print(f"→ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or REPO_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠️  {result.stderr.strip()}")
    else:
        print(f"  ✅ {result.stdout.strip()[:100]}")
    return result.returncode == 0


def main():
    """
    主部署流程。
    """
    os.chdir(REPO_DIR)

    # ---- Step 1: 读取 GitHub Token ----
    if not TOKEN_FILE.exists():
        print("❌ .git_token not found. Run setup first.")
        sys.exit(1)
    token = TOKEN_FILE.read_text().strip()

    # ---- Step 2: 拉取最新代码（rebase 避免合并提交） ----
    run(["git", "pull", "origin", "main", "--rebase"])

    # ---- Step 3: 运行 RSS 扫描器 ----
    print("\n📡 Scanning RSS sources...")
    result = subprocess.run(
        [sys.executable, "scripts/rss_scanner.py"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Scanner failed: {result.stderr}")
        sys.exit(1)

    # ---- Step 4: 提交并推送 ----
    print("\n📤 Pushing to GitHub...")
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", "📡 Daily AI intel scan"])

    # 使用 OAuth2 token 进行认证推送（将 token 嵌入 HTTPS URL）
    push_url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"
    result = subprocess.run(
        ["git", "push", push_url, "main"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    if result.returncode == 0:
        print(f"\n🎉 Deployed! → https://ai.hjhai.xyz")
    else:
        # 检查是否为 "nothing to commit" 的正常情况
        if "nothing to commit" in result.stdout or "everything up-to-date" in result.stderr:
            print("✅ Already up to date.")
        else:
            print(f"⚠️  Push issue: {result.stderr}")


if __name__ == "__main__":
    main()
