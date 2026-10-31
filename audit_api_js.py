with open('frontend/js/api.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

print("=== API METHODS in frontend/js/api.js ===")
for m in re.finditer(r'async\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', text):
    print(f"async {m.group(1)}({m.group(2)})")
