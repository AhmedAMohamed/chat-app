
import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from text_utils import normalize_arabic

class SemanticSearchEngine:
    def __init__(self, data_dir="data"):
        self.model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
        self.data_dir = data_dir

    def _load_project_data(self, project_id):
        entries_path = os.path.join(self.data_dir, f"entries_{project_id}.json")
        index_path = os.path.join(self.data_dir, f"index_{project_id}.faiss")
        if not os.path.exists(entries_path) or not os.path.exists(index_path):
            return None, None
        with open(entries_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        index = faiss.read_index(index_path)
        return entries, index

    def search(self, query: str, project_id: str, top_k: int = 3, tags=None):
        entries, index = self._load_project_data(project_id)
        if not entries or not index:
            return []
        query_vec = self.model.encode([normalize_arabic(query)])
        D, I = index.search(np.array(query_vec), k=min(top_k, len(entries)))
        results = []
        for idx, i in enumerate(I[0]):
            results.append({
                "text": entries[i]["text"],
                "score": float(D[0][idx]),
                "timestamp": entries[i].get("timestamp")
            })
        return results

    def build_index(self, project_id: str, entries: list, index_path: str = None):
        texts = [normalize_arabic(e["text"]) for e in entries]
        vectors = self.model.encode(texts)
        dim = vectors.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(vectors))
        entries_path = os.path.join(self.data_dir, f"entries_{project_id}.json")
        if index_path is None:
            index_path = os.path.join(self.data_dir, f"index_{project_id}.faiss")
        with open(entries_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        faiss.write_index(index, index_path)


