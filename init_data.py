
import os
import json
from datetime import datetime
from search_engine import SemanticSearchEngine
from text_utils import normalize_arabic

project_id = "P123"
data_dir = "data"
entries_path = os.path.join(data_dir, f"entries_{project_id}.json")
index_path = os.path.join(data_dir, f"index_{project_id}.faiss")

new_entries = [
    {
        "project_id": project_id,
        "text": "تم تأجيل التسليم بسبب مشكلة في الواجهة الخلفية",
        "timestamp": datetime.utcnow().isoformat()
    },
    {
        "project_id": project_id,
        "text": "تمت الموافقة على التسليم النهائي من قبل العميل",
        "timestamp": datetime.utcnow().isoformat()
    }
]

if os.path.exists(entries_path):
    with open(entries_path, "r", encoding="utf-8") as f:
        try:
            existing_entries = json.load(f)
        except Exception as e:
            print(f"[!] Failed to load existing entries: {e}")
            existing_entries = []
else:
    existing_entries = []

combined_entries = existing_entries + new_entries

seen = set()
deduped_entries = []
for e in combined_entries:
    if not isinstance(e, dict):
        print(f"[!] Skipping non-dictionary entry: {e}")
        continue

    text = e.get("text", "")
    if not isinstance(text, str) or not text.strip():
        print(f"[!] Skipping entry (invalid text): {e}")
        continue

    norm_text = normalize_arabic(text)
    if norm_text not in seen:
        seen.add(norm_text)
        deduped_entries.append(e)

with open(entries_path, "w", encoding="utf-8") as f:
    json.dump(deduped_entries, f, ensure_ascii=False, indent=2)

engine = SemanticSearchEngine(data_dir=data_dir)
engine.build_index(project_id, deduped_entries, index_path=index_path)

print(f"[✓] Re-indexed {len(deduped_entries)} entries for project {project_id}")
