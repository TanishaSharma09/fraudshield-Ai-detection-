with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="view-alerts"')
print(text[idx:idx+2000])
