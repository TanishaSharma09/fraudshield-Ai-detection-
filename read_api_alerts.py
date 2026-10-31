with open('frontend/js/api.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('markAlertReviewed')
print(text[idx-20:idx+1500])
