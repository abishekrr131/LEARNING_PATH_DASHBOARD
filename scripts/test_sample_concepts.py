import json

with open('database/seed/concepts_dump.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total concepts loaded: {len(data)}")
for d in data[::40]:
    print(f"Target: {d['target_name']:<30} | Topic: {d['topic_name']:<35} | Concept: {d['concept_name']}")
