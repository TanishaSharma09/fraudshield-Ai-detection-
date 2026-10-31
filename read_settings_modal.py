with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('settings-modal')
print(text[idx+1500:idx+3500])
