with open('backend/services/alert_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'def\s+([a-zA-Z0-9_]+)', text):
    print(m.group(1))
