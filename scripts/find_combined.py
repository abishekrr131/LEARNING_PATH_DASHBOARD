with open('backend/app/services/question_generator.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'combined' in line:
            print(f'{i+1}: {line.strip()}')
