import os
from pathlib import Path

base = Path('output/kalshi')
files = [
    'welcome.md',
    'api_environments.md',
    'api_keys.md',
    'market_lifecycle.md',
    'orderbook_responses.md',
    'quick_start_market_data.md',
    'quick_start_create_order.md',
    'rate_limits.md',
    'historical_data.md',
]

sections = []
for fname in files:
    path = base / fname
    if not path.exists():
        continue
    text = path.read_text(encoding='utf-8', errors='ignore')
    sections.append(f"\n\n## Source: {fname}\n\n" + text)

# Also mention specs but not inline their content
spec_note = "\n\n## Machine-Readable Specs\n\nThe full REST schema is in `kalshi_openapi.yaml` and WebSocket channels in `kalshi_asyncapi.yaml`. Use these alongside this overview for tool-building and codegen."

md = "# Kalshi Prediction Markets API v2 Overview for LLMs\n\n" \
     "This file consolidates core human-readable docs plus pointers to machine-readable specs, optimized for local LLM consumption.\n" + spec_note + "".join(sections)

out_path = Path('output/kalshi_api_llm_overview.md')
out_path.write_text(md, encoding='utf-8')

print(str(out_path))