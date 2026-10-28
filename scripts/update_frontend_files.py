"""Update frontend client.js to add getResourceDetail."""
import os

client_path = "C:/Users/abish/.gemini/antigravity/scratch/personalized-learning-dashboard/frontend/src/api/client.js"

with open(client_path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\r\n", "\n")

target = """  getCareerMap: (targetId) => {
    const query = targetId ? `?target_id=${targetId}` : "";
    return apiRequest(`/learning/career-map${query}`);
  },"""

replacement = """  getCareerMap: (targetId) => {
    const query = targetId ? `?target_id=${targetId}` : "";
    return apiRequest(`/learning/career-map${query}`);
  },
  getResourceDetail: (id) => apiRequest(`/learning/resources/${id}`),"""

if "getResourceDetail" not in text:
    assert target in text, "Could not find target in client.js"
    text = text.replace(target, replacement)
    with open(client_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("[OK] client.js updated with getResourceDetail!")
else:
    print("getResourceDetail already in client.js")
