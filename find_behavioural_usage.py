import glob

for py in glob.glob('backend/**/*.py', recursive=True) + glob.glob('ml_model/**/*.py', recursive=True):
    with open(py, 'r', encoding='utf-8') as f:
        c = f.read()
    if 'BehaviouralAnomalyDetector' in c or 'baseline_tracker' in c:
        print(f"Used in: {py}")
