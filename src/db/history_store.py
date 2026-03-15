import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class QueryHistoryDB:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_type TEXT NOT NULL,                -- hybrid | llm_hybrid
                    original_query TEXT NOT NULL,
                    processed_query TEXT,                  -- query sau khi LLM rewrite
                    top_k INTEGER NOT NULL DEFAULT 1,
                    results_json TEXT NOT NULL,            -- lưu raw results dạng JSON string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def insert_history(
        self,
        api_type: str,
        original_query: str,
        processed_query: Optional[str],
        top_k: int,
        results: List[Dict[str, Any]]
    ) -> int:
        results_json = json.dumps(results, ensure_ascii=False)

        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO query_history (
                    api_type, original_query, processed_query, top_k, results_json
                )
                VALUES (?, ?, ?, ?, ?)
            """, (api_type, original_query, processed_query, top_k, results_json))
            conn.commit()
            return cursor.lastrowid

    def get_history(
        self,
        api_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT id, api_type, original_query, processed_query, top_k, results_json, created_at
            FROM query_history
        """
        params = []

        if api_type:
            query += " WHERE api_type = ?"
            params.append(api_type)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            item = dict(row)
            item["results"] = json.loads(item.pop("results_json"))
            results.append(item)

        return results

    def get_by_id(self, history_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT id, api_type, original_query, processed_query, top_k, results_json, created_at
                FROM query_history
                WHERE id = ?
            """, (history_id,)).fetchone()

        if not row:
            return None

        item = dict(row)
        item["results"] = json.loads(item.pop("results_json"))
        return item