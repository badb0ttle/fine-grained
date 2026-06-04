import sys, json
sys.path.insert(0, '/Users/mac/Desktop/Projects/ai-intel')
from scripts.pipeline.model_tracker import get_candidate_articles, get_extraction_prompt

articles = get_candidate_articles(20)
print(f"Candidate articles for model extraction: {len(articles)}")

if articles:
    prompt = get_extraction_prompt(articles)
    with open('data/model_extraction_prompt.txt', 'w') as f:
        f.write(prompt)
    print(f"Prompt written ({len(prompt)} chars)")
else:
    print("No candidates found.")
