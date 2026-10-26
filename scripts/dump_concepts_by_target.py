import json

with open("database/seed/concepts_dump.json", "r", encoding="utf-8") as f:
    concepts = json.load(f)

for tid in range(1, 8):
    t_concepts = [c for c in concepts if c["target_id"] == tid]
    tname = t_concepts[0]["target_name"] if t_concepts else ""
    print(f"\n=================== TARGET {tid}: {tname} ({len(t_concepts)} concepts) ===================")
    by_topic = {}
    for c in t_concepts:
        by_topic.setdefault(c["topic_name"], []).append(c["concept_name"])
    for topic, cnames in by_topic.items():
        print(f"  Topic: {topic}")
        for cn in cnames:
            print(f"    - {cn}")
