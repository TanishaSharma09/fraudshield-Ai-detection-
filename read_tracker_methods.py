with open('ml_model/behavioural/baseline_tracker.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(185, 235):
    print(f"{i+1}: {lines[i]}", end='')
