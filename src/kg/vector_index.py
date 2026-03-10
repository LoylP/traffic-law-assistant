#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
STRUCTURED_DIR = DATA_DIR / "structured"
KG_DIR = DATA_DIR / "kg"
KG_DIR.mkdir(parents=True, exist_ok=True)

VIOLATION_FILE = STRUCTURED_DIR / "violations_300.json"
INDEX_FILE = KG_DIR / "faiss_index.bin"
META_FILE = KG_DIR / "faiss_meta.json"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def load_violations():
    with VIOLATION_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_index():
    data = load_violations()
    model = SentenceTransformer(MODEL_NAME)

    texts = []
    meta = []

    for item in data:
        violation_id = str(item.get("violation_id", "")).strip()
        if not violation_id:
            continue

        text = " | ".join([
            item.get("description_natural", "") or "",
            item.get("normalized_violation", "") or "",
            item.get("vehicle_type", "") or "",
            item.get("context_condition", "") or ""
        ]).strip()

        texts.append(text)
        meta.append({
            "node_id": f"VIOLATION_{violation_id}",
            "violation_id": violation_id,
            "text": text,
            "description_natural": item.get("description_natural", ""),
            "normalized_violation": item.get("normalized_violation", ""),
            "legal_basis": item.get("legal_basis", ""),
            "vehicle_type": item.get("vehicle_type", ""),
            "context_condition": item.get("context_condition", ""),
            "fine_min": item.get("fine_min"),
            "fine_max": item.get("fine_max"),
            "additional_sanctions": item.get("additional_sanctions", ""),
            "confidence_label": item.get("confidence_label", ""),
        })

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )
    embeddings = np.array(embeddings, dtype="float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_FILE))

    with META_FILE.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Saved index -> {INDEX_FILE}")
    print(f"Saved meta -> {META_FILE}")
    print(f"Indexed records -> {len(meta)}")


def search(query: str, top_k: int = 5):
    model = SentenceTransformer(MODEL_NAME)
    index = faiss.read_index(str(INDEX_FILE))

    with META_FILE.open("r", encoding="utf-8") as f:
        meta = json.load(f)

    q_emb = model.encode([query], normalize_embeddings=True)
    q_emb = np.array(q_emb, dtype="float32")

    scores, indices = index.search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        results.append({
            "score": float(score),
            **meta[idx]
        })
    return results


if __name__ == "__main__":
    build_index()
    rs = search("xe máy vượt đèn đỏ", top_k=3)
    print(json.dumps(rs, ensure_ascii=False, indent=2))