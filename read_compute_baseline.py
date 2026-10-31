with open('ml_model/behavioural/baseline_tracker.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def compute_baseline_from_records')
print(text[idx:idx+1200])
