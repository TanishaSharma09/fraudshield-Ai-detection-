with open('frontend/js/dashboard.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('bindManagementEvents() {')
print(text[idx:idx+2000])
