with open('backend/services/analytics_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'def ' in line:
        print(f"Line {idx+1}: {line.strip()}")
