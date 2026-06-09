import subprocess, os

os.chdir('/root/fine-grained')
token = open('.git_token').read().strip()
url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"

# Git add all
result = subprocess.run(["git", "add", "-A"], cwd=".", check=True, capture_output=True, text=True)
print("git add:", result.returncode)

# Git commit
result = subprocess.run(["git", "commit", "-m", "AI intel daily scan 2026-06-09"], cwd=".", capture_output=True, text=True)
print("git commit:", result.stdout.strip(), result.stderr.strip())

# Git push
result = subprocess.run(["git", "push", url, "main"], cwd=".", capture_output=True, text=True, timeout=60)
print("git push:", result.stdout.strip(), result.stderr.strip() if result.stderr else "")
print("exit code:", result.returncode)
