with open('frontend/js/dashboard.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('alert-stat-total')
print(text[idx-400:idx+100])
