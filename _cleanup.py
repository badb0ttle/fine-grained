import subprocess, os

os.chdir('/root/fine-grained')
token = open('.git_token').read().strip()
url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"

subprocess.run(["git", "add", "-A"], cwd=".", check=True)
result = subprocess.run(["git", "commit", "-m", "Clean up temp cron scripts"], cwd=".", capture_output=True, text=True)
print("commit:", result.stdout.strip(), result.stderr.strip())

result = subprocess.run(["git", "push", url, "main"], cwd=".", capture_output=True, text=True, timeout=60)
print("push:", result.stdout.strip(), result.stderr.strip() if result.stderr else "")

# Clean up this script itself
os.remove('/root/fine-grained/_cleanup.py')
print("Self-deleted")
