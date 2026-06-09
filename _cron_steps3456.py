import json, urllib.request, sys, os
sys.path.insert(0, '/root/fine-grained/scripts')

API_KEY = "sk-35b07bd3aac2422fa717de9512137c37"
BASE = '/root/fine-grained'

# ============================================================
# Step 3: Apply Curation
# ============================================================
from pipeline.curator import apply_curation
curated = json.load(open(f'{BASE}/data/curated.json'))
apply_curation(curated)
print(f"[Step 3] ✅ Applied curation for {len(curated)} articles")

# ============================================================
# Step 4: Paper Analysis
# ============================================================
from pipeline.paper_analyzer import get_unanalyzed_papers, get_analysis_prompt, apply_analysis

papers = get_unanalyzed_papers(10)
if papers:
    prompt = get_analysis_prompt(papers)
    req = urllib.request.Request(
        'https://api.deepseek.com/v1/chat/completions',
        data=json.dumps({
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.2,
            'max_tokens': 4096
        }).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
    )
    resp = urllib.request.urlopen(req, timeout=180)
    content = json.loads(resp.read())['choices'][0]['message']['content']
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0]
    elif '```' in content:
        content = content.split('```')[1].split('```')[0]
    results = json.loads(content.strip())
    apply_analysis(results)
    print(f"[Step 4] ✅ Papers analyzed: {len(results)}")
else:
    print("[Step 4] ⏭️  No unanalyzed papers")

# ============================================================
# Step 5: Model Tracking
# ============================================================
from pipeline.model_tracker import get_candidate_articles, get_extraction_prompt, apply_models

articles = get_candidate_articles(20)
if articles:
    prompt = get_extraction_prompt(articles)
    req = urllib.request.Request(
        'https://api.deepseek.com/v1/chat/completions',
        data=json.dumps({
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.2,
            'max_tokens': 4096
        }).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
    )
    resp = urllib.request.urlopen(req, timeout=180)
    content = json.loads(resp.read())['choices'][0]['message']['content']
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0]
    elif '```' in content:
        content = content.split('```')[1].split('```')[0]
    results = json.loads(content.strip())
    apply_models(results)
    print(f"[Step 5] ✅ Models extracted: {len(results)}")
else:
    print("[Step 5] ⏭️  No candidate articles for model extraction")

# ============================================================
# Step 6: Paper-Code Linking
# ============================================================
from pipeline.paper_code_link import run as link_papers
from pathlib import Path

token = Path(f'{BASE}/.git_token').read_text().strip()
result = link_papers(limit=5, token=token)
print(f"[Step 6] ✅ Paper-code linking done: {result}")
