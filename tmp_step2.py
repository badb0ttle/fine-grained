import sys
sys.path.insert(0, '/Users/mac/Desktop/Projects/ai-intel')

from scripts.pipeline.paper_analyzer import get_unanalyzed_papers, get_analysis_prompt

papers = get_unanalyzed_papers(10)
print(f"Unanalyzed papers: {len(papers)}")

if not papers:
    print("No unanalyzed papers found.")
    sys.exit(0)

prompt = get_analysis_prompt(papers)
with open('data/paper_analysis_prompt.txt', 'w') as f:
    f.write(prompt)
print(f"Prompt written to data/paper_analysis_prompt.txt ({len(prompt)} chars)")
