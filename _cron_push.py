import subprocess
import os

os.chdir('/root/fine-grained')

token = open('.git_token').read().strip()
url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"

# Clean up cron temp scripts
for f in ['_cron_step2.py', '_cron_step3.py', '_cron_step4.py', '_cron_step5.py', '_cron_step6.py']:
    try:
        os.remove(f)
    except:
        pass

# Add and commit remaining files
subprocess.run(["git", "add", "-A"], check=True)
result = subprocess.run(["git", "commit", "-m", "AI intel daily scan 2026-06-07"], capture_output=True, text=True)
print(result.stdout.strip())
print(result.stderr.strip())

# Push
result = subprocess.run(["git", "push", url, "main"], capture_output=True, text=True, timeout=60)
print(result.stdout.strip())
print(result.stderr.strip())
print("✅ Manual push complete")
