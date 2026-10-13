import os
import re

frontend_dir = os.path.join("frontend", "src")
missing_usestate = []

for root, dirs, files in os.walk(frontend_dir):
    for f in files:
        if f.endswith(".jsx") or f.endswith(".js"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
            if "useState" in content:
                if not re.search(r"import\s+[^;]*useState[^;]*from\s+['\"]react['\"]", content):
                    missing_usestate.append(path)

print("Files missing useState import:")
for p in missing_usestate:
    print(f" - {p}")
