with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="mgmt-filter-channel"')
print(text[idx-50:idx+600])
