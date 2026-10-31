with open('frontend/js/dashboard.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re

print("=== METHODS in FraudShieldDashboard ===")
for idx, line in enumerate(lines):
    m = re.match(r'^\s{2}([a-zA-Z0-9_]+)\s*\((.*?)\)\s*\{', line)
    if m:
        print(f"Line {idx+1}: {m.group(1)}({m.group(2)})")
