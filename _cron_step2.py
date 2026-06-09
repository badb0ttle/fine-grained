import json, urllib.request, sys, os

sys.path.insert(0, '/root/fine-grained/scripts')

# Read curation prompt
prompt = open('/root/fine-grained/data/curation_prompt.txt', 'r').read()

# Call DeepSeek API (hardcoded key for cron env)
api_key = "sk-35b07bd3aac2422fa717de9512137c37"
req = urllib.request.Request(
    'https://api.deepseek.com/v1/chat/completions',
    data=json.dumps({
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.3,
        'max_tokens': 4096
    }).encode(),
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
)
resp = urllib.request.urlopen(req, timeout=180)
content = json.loads(resp.read())['choices'][0]['message']['content']

# Extract JSON from response (handle ```json ... ``` wrappers)
if '```json' in content:
    content = content.split('```json')[1].split('```')[0].strip()
elif '```' in content:
    content = content.split('```')[1].split('```')[0].strip()

results = json.loads(content.strip())
print(f"✅ Curated {len(results)} articles")

# Save to curated.json
with open('/root/fine-grained/data/curated.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("✅ Saved to data/curated.json")

# Print preview
for item in results[:3]:
    print(f"  [{item['id']}] {item['title_cn']}")
