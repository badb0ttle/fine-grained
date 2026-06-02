#!/usr/bin/env python3
"""Fetch week articles and generate prompt."""
import sys; sys.path.insert(0, '.')
from scripts.pipeline.weekly_report import get_week_articles, get_weekly_prompt
from pathlib import Path

data = get_week_articles(7)
prompt = get_weekly_prompt(data)

Path('data/weekly_prompt.txt').write_text(prompt)

print(f"Articles: {len(data['top_articles'])}, Curated: {data['curated_count']}")
print("=" * 60)
print(prompt)
