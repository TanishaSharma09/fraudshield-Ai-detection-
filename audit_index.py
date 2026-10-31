import re
import glob

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

print('=== VIEWS in index.html ===')
for m in re.finditer(r'<div\s+[^>]*id=["\'](view-[a-zA-Z0-9_\-]+)["\']', text):
    print(m.group(1))

print('\n=== NAV ITEMS in index.html ===')
for m in re.finditer(r'<a\s+class=["\']nav-item[^"\']*["\']([^>]*)>(.*?)</a>', text, re.DOTALL):
    attrs = m.group(1)
    content = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()
    print(f'Attrs: {attrs.strip()} | Label: {content}')

print('\n=== MODALS / DRAWERS ===')
for m in re.finditer(r'id=["\']([a-zA-Z0-9_\-]*(?:modal|drawer)[a-zA-Z0-9_\-]*)["\']', text):
    print(m.group(1))
