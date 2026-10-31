with open('frontend/js/dashboard.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('btn-modal-block-tx')
print(text[idx-50:idx+600])
