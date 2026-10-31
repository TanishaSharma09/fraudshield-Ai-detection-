with open('backend/api/routes_analytics.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines[:100]):
    if '@router' in line or 'def ' in line:
        print(f"{idx+1}: {line.strip()}")
