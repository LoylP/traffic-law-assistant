from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

import faiss
import networkx as nx
import numpy as np
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
KG_DIR = DATA_DIR / "kg"

KG_NODES_FILE = KG_DIR / "kg_nodes.jsonl"
KG_EDGES_FILE = KG_DIR / "kg_edges.jsonl"
FAISS_INDEX_FILE = KG_DIR / "faiss_index.bin"
FAISS_META_FILE = KG_DIR / "faiss_meta.json"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _norm(text: Any) -> str:
    if text is None:
        return ""
    text = str(text).lower().strip()
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class TrafficLawGraphQuery:
    def __init__(
        self,
        kg_nodes_file: Path = KG_NODES_FILE,
        kg_edges_file: Path = KG_EDGES_FILE,
        faiss_index_file: Path = FAISS_INDEX_FILE,
        faiss_meta_file: Path = FAISS_META_FILE,
        model_name: str = MODEL_NAME,
    ):
        self.kg_nodes_file = Path(kg_nodes_file)
        self.kg_edges_file = Path(kg_edges_file)
        self.faiss_index_file = Path(faiss_index_file)
        self.faiss_meta_file = Path(faiss_meta_file)
        self.model_name = model_name

        self.graph = nx.MultiDiGraph()
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.faiss_index = None
        self.faiss_meta: List[Dict[str, Any]] = []
        self.model = None

    # =========================
    # LOAD
    # =========================
    def load_all(self):
        self._load_graph()
        self._load_faiss()
        self._load_model()

    def _load_model(self):
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def _load_graph(self):
        if not self.kg_nodes_file.exists():
            raise FileNotFoundError(f"Không tìm thấy file nodes: {self.kg_nodes_file}")
        if not self.kg_edges_file.exists():
            raise FileNotFoundError(f"Không tìm thấy file edges: {self.kg_edges_file}")

        self.graph = nx.MultiDiGraph()
        self.nodes = {}

        with self.kg_nodes_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                node = json.loads(line)
                node_id = node["id"]
                self.nodes[node_id] = node
                self.graph.add_node(node_id, **node)

        with self.kg_edges_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                edge = json.loads(line)
                src = edge["source"]
                dst = edge["target"]
                rel = edge["relation"]
                self.graph.add_edge(src, dst, key=rel, **edge)

    def _load_faiss(self):
        if not self.faiss_index_file.exists():
            raise FileNotFoundError(f"Không tìm thấy file FAISS index: {self.faiss_index_file}")
        if not self.faiss_meta_file.exists():
            raise FileNotFoundError(f"Không tìm thấy file FAISS meta: {self.faiss_meta_file}")

        self.faiss_index = faiss.read_index(str(self.faiss_index_file))

        with self.faiss_meta_file.open("r", encoding="utf-8") as f:
            self.faiss_meta = json.load(f)

    # =========================
    # GRAPH HELPERS
    # =========================
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(node_id)

    def neighbors_by_relation(
        self,
        node_id: str,
        relation: Optional[str] = None,
        direction: str = "out"
    ) -> List[Dict[str, Any]]:
        results = []

        if direction in {"out", "both"}:
            for _, dst, key, data in self.graph.out_edges(node_id, keys=True, data=True):
                if relation is None or data.get("relation") == relation:
                    results.append({
                        "direction": "out",
                        "relation": data.get("relation"),
                        "edge": data,
                        "node": self.get_node(dst),
                    })

        if direction in {"in", "both"}:
            for src, _, key, data in self.graph.in_edges(node_id, keys=True, data=True):
                if relation is None or data.get("relation") == relation:
                    results.append({
                        "direction": "in",
                        "relation": data.get("relation"),
                        "edge": data,
                        "node": self.get_node(src),
                    })

        return results

    def _all_neighbor_nodes(self, node_id: str, relation: str) -> List[Dict[str, Any]]:
        out = self.neighbors_by_relation(node_id, relation=relation, direction="out")
        return [x["node"] for x in out if x.get("node")]

    # =========================
    # SEMANTIC SEARCH
    # =========================
    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        self._load_model()

        q_emb = self.model.encode([query], normalize_embeddings=True)
        q_emb = np.array(q_emb, dtype="float32")

        scores, indices = self.faiss_index.search(q_emb, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if idx >= len(self.faiss_meta):
                continue

            meta = self.faiss_meta[idx]
            node_id = meta.get("node_id")

            node = self.get_node(node_id) if node_id else None

            # fallback nếu meta bị thiếu / lệch id
            if node is None and meta.get("violation_id"):
                fallback_id = f"VIOLATION_{meta['violation_id']}"
                node = self.get_node(fallback_id)
                if node is not None:
                    node_id = fallback_id

            results.append({
                "score": float(score),
                "meta": meta,
                "node_id": node_id,
                "node": node,
            })
        return results

    # =========================
    # HYBRID RERANK
    # =========================
    def _keyword_bonus(self, query: str, node: Dict[str, Any]) -> float:
        q = _norm(query)
        text = " ".join([
            _norm(node.get("description_natural", "")),
            _norm(node.get("normalized_violation", "")),
            _norm(node.get("vehicle_type", "")),
            _norm(node.get("context_condition", "")),
        ])

        if not q or not text:
            return 0.0

        q_tokens = set(q.split())
        t_tokens = set(text.split())

        overlap = len(q_tokens & t_tokens)
        bonus = overlap * 0.03

        # boost nhẹ theo vehicle
        if "xe may" in q and "xe may" in text:
            bonus += 0.08
        if "o to" in q and "o to" in text:
            bonus += 0.08
        if "xe dap" in q and "xe dap" in text:
            bonus += 0.08
        if "cao toc" in q and "cao toc" in text:
            bonus += 0.06
        if "mu bao hiem" in q and "mu bao hiem" in text:
            bonus += 0.08
        if "den tin hieu" in q and "den tin hieu" in text:
            bonus += 0.08
        if "vuot den do" in q and ("den tin hieu" in text or "khong chap hanh hieu lenh cua den tin hieu" in text):
            bonus += 0.12

        return bonus

    # =========================
    # DOMAIN QUERY
    # =========================
    def get_violation_bundle(self, violation_node_id: str) -> Optional[Dict[str, Any]]:
        violation_node = self.get_node(violation_node_id)
        if not violation_node:
            return None

        legal_nodes = self._all_neighbor_nodes(violation_node_id, "BASED_ON")
        vehicle_nodes = self._all_neighbor_nodes(violation_node_id, "APPLIES_TO")

        return {
            "violation": violation_node,
            "vehicle_types": vehicle_nodes,
            "legal_basis_nodes": legal_nodes,
        }

    def query_violation(self, user_query: str, top_k: int = 5) -> Dict[str, Any]:
        semantic_hits = self.semantic_search(user_query, top_k=max(top_k, 10))

        violation_results = []
        seen_violation_ids = set()

        reranked = []
        for hit in semantic_hits:
            node = hit.get("node")
            if not node:
                continue
            if node.get("type") != "Violation":
                continue

            score = float(hit["score"]) + self._keyword_bonus(user_query, node)
            reranked.append({
                "score": score,
                "raw_score": float(hit["score"]),
                "node": node,
            })

        reranked.sort(key=lambda x: x["score"], reverse=True)

        for hit in reranked:
            node = hit["node"]
            node_id = node["id"]

            if node_id in seen_violation_ids:
                continue
            seen_violation_ids.add(node_id)

            bundle = self.get_violation_bundle(node_id)
            if not bundle:
                continue

            violation_results.append({
                "score": hit["score"],
                "raw_score": hit["raw_score"],
                **bundle
            })

            if len(violation_results) >= top_k:
                break

        return {
            "query": user_query,
            "semantic_hits": semantic_hits,
            "violation_results": violation_results
        }

    # =========================
    # ANSWER FORMATTER
    # =========================
    @staticmethod
    def _format_money(v: Optional[Any]) -> Optional[str]:
        if v is None:
            return None
        try:
            return f"{int(v):,}".replace(",", ".") + " đồng"
        except Exception:
            return str(v)

    def build_answer_from_bundle(self, bundle_result: Dict[str, Any]) -> Dict[str, Any]:
        violation = bundle_result["violation"]
        legal_basis_nodes = bundle_result.get("legal_basis_nodes", [])

        fine_min = violation.get("fine_min")
        fine_max = violation.get("fine_max")

        legal_basis = []
        for ln in legal_basis_nodes:
            legal_basis.append({
                "citation_id": ln.get("citation_id"),
                "decree_no": ln.get("decree_no"),
                "article": ln.get("article"),
                "clause": ln.get("clause"),
                "point": ln.get("point"),
                "text": ln.get("text"),
                "source": ln.get("source"),
            })

        additional_sanctions = violation.get("additional_sanctions", [])
        if isinstance(additional_sanctions, str):
            additional_sanctions = [additional_sanctions] if additional_sanctions.strip() else []

        return {
            "violation_id": violation.get("violation_id"),
            "description": violation.get("description_natural") or violation.get("normalized_violation"),
            "normalized_violation": violation.get("normalized_violation"),
            "vehicle_type": violation.get("vehicle_type"),
            "fine_min": fine_min,
            "fine_max": fine_max,
            "fine_min_text": self._format_money(fine_min),
            "fine_max_text": self._format_money(fine_max),
            "additional_sanctions": additional_sanctions,
            "remedies": [],
            "legal_basis": legal_basis,
        }

    def answer(self, user_query: str, top_k: int = 5, score_threshold: float = 0.1) -> Dict[str, Any]:
        result = self.query_violation(user_query, top_k=top_k)
        violation_results = result["violation_results"]

        if not violation_results:
            return {
                "query": user_query,
                "found": False,
                "message": "Không biết / Không có dữ liệu phù hợp."
            }

        best = violation_results[0]
        if best["score"] < score_threshold:
            return {
                "query": user_query,
                "found": False,
                "message": "Không biết / Không có dữ liệu phù hợp.",
                "best_score": best["score"]
            }

        answer = self.build_answer_from_bundle(best)
        return {
            "query": user_query,
            "found": True,
            "best_score": best["score"],
            "answer": answer,
            "candidates": [
                {
                    "score": item["score"],
                    "violation_id": item["violation"].get("violation_id"),
                    "label": item["violation"].get("description_natural") or item["violation"].get("normalized_violation")
                }
                for item in violation_results[:5]
            ]
        }


if __name__ == "__main__":
    engine = TrafficLawGraphQuery()
    engine.load_all()

    rs = engine.answer("xe máy vượt đèn đỏ", top_k=5, score_threshold=0.1)
    print(json.dumps(rs, ensure_ascii=False, indent=2))