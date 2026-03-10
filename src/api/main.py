# -*- coding: utf-8 -*-
"""FastAPI app: search API + ingest API + web UI for testing."""

from __future__ import annotations

from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.search.ingest import load_knowledge
from src.search.search_service import search

app = FastAPI(title="Traffic Law Search", version="0.1.0")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _allowed_ingest_path(path: str) -> Path:
    """Resolve path; allow only under project root and under data/structured/."""
    full = (PROJECT_ROOT / path).resolve()
    if not full.is_relative_to(PROJECT_ROOT) or not path.replace("\\", "/").startswith("data/structured/"):
        raise HTTPException(status_code=400, detail="path must be under data/structured/")
    return full


def _fallback_html() -> str:
    return """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Traffic Law Search</title></head>
<body><h1>Traffic Law Search</h1><input id="q" placeholder="Search..." />
<button onclick="fetch('/api/search?q='+encodeURIComponent(document.getElementById('q').value)).then(r=>r.json()).then(d=>alert(JSON.stringify(d,null,2)))">Search</button></body></html>"""

UI_HTML_PATH = Path(__file__).resolve().parent / "static" / "index.html"


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Serve the search UI."""
    if UI_HTML_PATH.exists():
        return HTMLResponse(content=UI_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content=_fallback_html(), status_code=200)


@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1, description="Search query")) -> JSONResponse:
    """Search traffic violations by natural language. Returns top_k results with score."""
    try:
        results = search(q)
        return JSONResponse(content={"query": q, "results": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class IngestBody(BaseModel):
    source: str  # "violations" | "jsonl"
    path: str | None = None  # optional, under data/structured/


@app.post("/api/ingest")
def api_ingest(body: IngestBody = Body(...)):
    """
    Load knowledge into the vector DB.
    Body: { "source": "violations" | "jsonl", "path": optional path under data/structured/ }.
    """
    source = body.source
    if source not in ("violations", "jsonl"):
        raise HTTPException(status_code=400, detail="source must be 'violations' or 'jsonl'")
    path = body.path or ("violations_300.json" if source == "violations" else "law_corpus.jsonl")
    if not path.startswith("data/"):
        path = f"data/structured/{path}"
    full = _allowed_ingest_path(path)
    if not full.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        count = load_knowledge(source, full)
        return JSONResponse(content={"source": source, "path": path, "indexed": count})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
