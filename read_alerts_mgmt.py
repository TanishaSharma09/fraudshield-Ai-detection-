with open('frontend/js/dashboard.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'async\s+loadAlertsManagement', text):
    print(text[m.start():m.start()+1500])
