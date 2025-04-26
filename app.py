from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import json
from search_engine import SemanticSearchEngine
from text_utils import normalize_arabic

def summarize_entries(entries, lang="ar"):
    if not entries:
        return "لم يتم العثور على تحديث مرتبط بالاستفسار." if lang == "ar" else "No relevant updates found."
    if lang == "ar":
        reply = f"نعم، تم العثور على {len(entries)} تحديثات ذات صلة:\n"
        for e in entries:
            reply += f"- '{e['text']}' بتاريخ {e['timestamp'][:10]}\n"
    else:
        reply = f"Yes, {len(entries)} relevant updates found:\n"
        for e in entries:
            reply += f"- '{e['text']}' on {e['timestamp'][:10]}\n"
    return reply.strip()

import requests

app = FastAPI()
search_engine = SemanticSearchEngine()
DATA_DIR = "data"

ALLOWED_IPS = {"127.0.0.1", "::1"}

@app.middleware("http")
async def restrict_to_whitelist(request: Request, call_next):
    client_ip = request.client.host
    if client_ip not in ALLOWED_IPS:
        return JSONResponse(status_code=403, content={"detail": f"Access denied for IP: {client_ip}"})
    return await call_next(request)

class QueryRequest(BaseModel):
    query: str

class EntryInput(BaseModel):
    project_id: str
    text: str
    timestamp: Optional[str] = None

def detect_intent(query: str) -> str:
    query = query.lower()
    latest_keywords = [
        "latest", "current", "now", "update", "recent", 
        "آخر", "الأخيرة", "الراهنة", "الوقت الحالي", "مستجدات", "التحديث"
    ]
    for k in latest_keywords:
        if k in query:
            return "latest"
    return "semantic"
    return "latest" if any(k in query for k in keywords) else "semantic"

def contains_english(text):
    return any('a' <= c.lower() <= 'z' for c in text)

def ask_local_llm(query, entries):
    context = "\n".join(f"- {e['text']} ({e['timestamp'][:10]})" for e in entries)
    is_arabic = any(c in query for c in 'ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوي')

    def generate(prompt):
        try:
            response = requests.post("http://localhost:11434/api/generate", json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }, timeout=30)
            return response.json().get("response", "No reply generated.")
        except Exception as e:
            return f"LLM error: {str(e)}"

    if is_arabic:
        system_prompt = (
            "أنت مساعد ذكي لمتابعة المشاريع. استخدم المعلومات التالية للإجابة على استفسار المستخدم:\n"
            f"السؤال: {query}\n"
            f"التحديثات:\n{context}\n\n"
            "يرجى إعطاء إجابة دقيقة وموجزة بناءً على التحديثات أعلاه.\n"
            "أجب باللغة العربية فقط."
        )
        reply = generate(system_prompt)

        # Fallback if LLM responds in English
        if contains_english(reply):
            system_prompt += "\nكرر الإجابة ولكن تأكد أن تكون بالكامل باللغة العربية دون أي كلمات إنجليزية."
            reply = generate(system_prompt)
        return reply
    else:
        system_prompt = (
            f"You are a smart assistant for project updates. Based on the following user question and related updates:\n"
            f"Question: {query}\n"
            f"Updates:\n{context}\n\n"
            f"Answer clearly and concisely in English."
        )
        return generate(system_prompt)

@app.post("/search")
def search(request: QueryRequest):
    try:
        with open(os.path.join(DATA_DIR, "projects.json"), "r", encoding="utf-8") as f:
            projects = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to load projects.json")

    matched_project = next((p for p in projects if p["name"].lower() in request.query.lower()), None)
    if not matched_project:
        raise HTTPException(status_code=404, detail="No project matched the query.")

    project_id = matched_project["project_id"]
    entries_path = os.path.join(DATA_DIR, f"entries_{project_id}.json")
    if not os.path.exists(entries_path):
        raise HTTPException(status_code=404, detail=f"No entries found for {matched_project['name']}")

    with open(entries_path, "r", encoding="utf-8") as f:
        all_entries = json.load(f)

    if not all_entries:
        raise HTTPException(status_code=404, detail="No updates found for this project.")

    intent = detect_intent(request.query)

    if intent == "latest":
        latest = sorted(all_entries, key=lambda x: x["timestamp"], reverse=True)[0]
        return {
            "intent": "latest",
            "project": matched_project["name"],
            "entry": latest
        }
    # else:
    #     return{
    #         "intent": "latest",
    #         "project": matched_project["name"],
    #         "entry": "لست بالذكاء الكافي بعد، لكنني أتحسّن باستمرار"
    #     }

    # semantic
    lang = 'ar' if any(c in request.query for c in 'ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوي') else 'en'
    results = search_engine.search(query=request.query, project_id=project_id, top_k=3)
    reply_text = summarize_entries(results, lang=lang)
    llm_reply = ask_local_llm(request.query, results)

    return {
        "intent": "semantic",
        "project": matched_project["name"],
        "results": results,
        "reply": reply_text,
        "llm_reply": llm_reply
    }

@app.post("/add_entry")
def add_entry(entry: EntryInput):
    if not entry.text.strip():
        raise HTTPException(status_code=400, detail="Entry text cannot be empty.")
    entry_data = {
        "project_id": entry.project_id,
        "text": entry.text,
        "timestamp": entry.timestamp or datetime.utcnow().isoformat()
    }
    entries_path = os.path.join(DATA_DIR, f"entries_{entry.project_id}.json")
    entries = []
    if os.path.exists(entries_path):
        with open(entries_path, "r", encoding="utf-8") as f:
            try:
                entries = json.load(f)
            except Exception:
                pass
    entries.append(entry_data)
    with open(entries_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

@app.post("/reindex/{project_id}")
def reindex_project(project_id: str):
    entries_path = os.path.join(DATA_DIR, f"entries_{project_id}.json")
    if not os.path.exists(entries_path):
        raise HTTPException(status_code=404, detail="Project entries not found.")
    with open(entries_path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    if not entries:
        raise HTTPException(status_code=400, detail="No entries to index.")
    search_engine.build_index(project_id, entries)