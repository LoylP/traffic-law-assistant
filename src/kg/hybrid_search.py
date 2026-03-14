import json
import numpy as np
import pandas as pd
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import minmax_scale
from underthesea import word_tokenize

class LegalRetriever:
    def __init__(self, nodes_path, cache_dir, model_name="intfloat/multilingual-e5-large"):
        self.nodes_path = Path(nodes_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        print("--- Đang tải mô hình Embedding (E5) ---")
        self.model = SentenceTransformer(model_name)
        
        self.df_corpus = self._load_corpus()
        self.bm25, self.doc_embeddings = self._prepare_indices()

    def _tokenize_bm25(self, text):
        text = str(text).lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        segmented = word_tokenize(text, format="text")
        return segmented.split()

    def _load_corpus(self):
        print(f"--- Đang đọc dữ liệu từ: {self.nodes_path.name} ---")
        violation_rows = []
        if not self.nodes_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file {self.nodes_path}")
            
        with open(self.nodes_path, "r", encoding="utf-8") as f:
            for line in f:
                node = json.loads(line)
                if node.get("type") == "Violation":
                    # Kết hợp các trường để tăng độ chính xác khi tìm kiếm
                    text_search = f"{node.get('description_natural', '')} {node.get('normalized_violation', '')}"
                    violation_rows.append({
                        "violation_id": str(node.get("violation_id")),
                        "text": text_search,
                        "raw_node": node
                    })
        return pd.DataFrame(violation_rows).drop_duplicates(subset=["violation_id"])

    def _prepare_indices(self):
        # BM25 Index
        tokenized_corpus = [self._tokenize_bm25(t) for t in self.df_corpus["text"]]
        bm25 = BM25Okapi(tokenized_corpus)
        
        # E5 Embeddings Index
        emb_path = self.cache_dir / "e5_large_embeddings.npy"
        if emb_path.exists():
            print("--- Loading cached embeddings ---")
            doc_embeddings = np.load(emb_path)
        else:
            print("--- Encoding corpus (lần đầu sẽ hơi chậm) ---")
            passages = [f"passage: {t}" for t in self.df_corpus["text"]]
            doc_embeddings = self.model.encode(passages, normalize_embeddings=True, show_progress_bar=True)
            np.save(emb_path, doc_embeddings)
            
        return bm25, doc_embeddings

    def search(self, query, top_k=5, alpha=0.5):
        # BM25 Scoring
        tk_query = self._tokenize_bm25(query)
        bm25_scores = self.bm25.get_scores(tk_query)
        
        # Vector Scoring
        q_emb = self.model.encode([f"query: {query}"], normalize_embeddings=True)[0]
        emb_scores = np.dot(self.doc_embeddings, q_emb)

        # Hybrid Combination
        bm25_n = minmax_scale(bm25_scores) if np.ptp(bm25_scores) > 0 else np.zeros_like(bm25_scores)
        emb_n = minmax_scale(emb_scores) if np.ptp(emb_scores) > 0 else np.zeros_like(emb_scores)
        
        final_scores = alpha * bm25_n + (1 - alpha) * emb_n
        top_idx = np.argsort(final_scores)[::-1][:top_k]
        
        return self.df_corpus.iloc[top_idx].to_dict('records')