with open('frontend/js/dashboard.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'inspectTransaction\s*\(', text):
    print(text[m.start()-20:m.start()+1500])
    print('---')
