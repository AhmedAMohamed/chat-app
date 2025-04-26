import os
import json
from search_engine import SemanticSearchEngine

DATA_DIR = "data"
engine = SemanticSearchEngine(data_dir=DATA_DIR)

# Loop through all entries_*.json files in the data directory
for filename in os.listdir(DATA_DIR):
    if filename.startswith("entries_") and filename.endswith(".json"):
        project_id = filename[len("entries_"):-len(".json")]
        entries_path = os.path.join(DATA_DIR, filename)
        with open(entries_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        if entries:
            print(f"[+] Re-indexing project {project_id} ({len(entries)} entries)...")
            engine.build_index(project_id, entries)
        else:
            print(f"[!] Skipping {project_id} — no entries found.")

print("[✓] All projects reindexed.")
