import sys
sys.path.insert(0, '/Users/mac/Desktop/Projects/ai-intel')
from scripts.pipeline.paper_code_link import run
from pathlib import Path

token = Path('.git_token').read_text().strip()
result = run(limit=5, token=token)
print(f"Paper-code linking result: {result}")
