import subprocess
token = open('/Users/mac/Desktop/Projects/ai-intel/.git_token').read().strip()
url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"
subprocess.run(["git", "add", "-A"], cwd="/Users/mac/Desktop/Projects/ai-intel", check=True)
subprocess.run(["git", "commit", "-m", "Step 3-4: LLM curation - 10 articles curated"], 
              cwd="/Users/mac/Desktop/Projects/ai-intel", check=True)
result = subprocess.run(["git", "push", url, "main"], cwd="/Users/mac/Desktop/Projects/ai-intel", 
                       capture_output=True, text=True, timeout=60)
print(result.stdout)
print(result.stderr)
