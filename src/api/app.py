import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.kg.hybrid_search import LegalRetriever
from src.kg.llm_processor import GeminiQueryProcessor
from src.db.history_store import QueryHistoryDB


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
KG_DIR = DATA_DIR / "kg"
STRUCTURED_DIR = DATA_DIR / "structured"
DB_DIR = DATA_DIR / "db"

KG_NODES_FILE = KG_DIR / "kg_nodes.jsonl"
EMB_CACHE_DIR = KG_DIR / "embedding_cache"
AMENDMENT_MAP_FILE = STRUCTURED_DIR / "amendment_map.json"
SQLITE_DB_FILE = DB_DIR / "query_history.db"


def load_amendment_map(amendment_path: Path) -> Dict[str, Any]:
    if not amendment_path.exists():
        return {}

    with open(amendment_path, "r", encoding="utf-8") as f:
        amendment_map = json.load(f)

    # normalize key: bỏ _2019 nếu có
    normalized_amendment_map = {
        k.replace("_2019", ""): v for k, v in amendment_map.items()
    }
    return normalized_amendment_map


def enrich_result(result: Dict[str, Any], amendment_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bổ sung amendment info vào raw result trước khi trả về API.
    """
    result = dict(result)
    node = dict(result.get("raw_node", {}))

    citation_id = node.get("citation_id")
    amendments = amendment_map.get(citation_id, []) if citation_id else []

    node["amendments"] = amendments
    result["raw_node"] = node
    return result


class HybridSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu truy vấn gốc")
    top_k: int = Field(5, ge=1, le=20, description="Số kết quả muốn lấy")
    alpha: float = Field(0.5, ge=0.0, le=1.0, description="Trọng số BM25")


class LLMSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu truy vấn gốc")
    alpha: float = Field(0.5, ge=0.0, le=1.0, description="Trọng số BM25")


class SearchResponse(BaseModel):
    success: bool
    api_type: str
    original_query: str
    processed_query: Optional[str] = None
    vehicle_type: Optional[str] = None
    expand_queries: Optional[List[str]] = None
    top_k: int
    results: Optional[List[Dict[str, Any]]] = None
    best_result: Optional[Dict[str, Any]] = None


class HistoryResponse(BaseModel):
    success: bool
    total: int
    items: List[Dict[str, Any]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Đang khởi tạo FastAPI app...")

    if not KG_NODES_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file KG: {KG_NODES_FILE}")

    retriever = LegalRetriever(KG_NODES_FILE, EMB_CACHE_DIR)
    llm_engine = GeminiQueryProcessor()
    amendment_map = load_amendment_map(AMENDMENT_MAP_FILE)
    history_db = QueryHistoryDB(SQLITE_DB_FILE)

    app.state.retriever = retriever
    app.state.llm_engine = llm_engine
    app.state.amendment_map = amendment_map
    app.state.history_db = history_db

    print("FastAPI app sẵn sàng.")
    yield
    print("Đóng FastAPI app...")


app = FastAPI(
    title="Traffic Law Search API",
    version="1.0.0",
    description="API tra cứu luật giao thông bằng hybrid search và LLM + hybrid search",
    lifespan=lifespan,
)

# CORS cho phép frontend truy cập từ máy khác (dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Traffic Law Search API is running",
        "docs": "/docs"
    }


@app.post("/search/hybrid", response_model=SearchResponse)
def search_hybrid(payload: HybridSearchRequest):
    try:
        retriever: LegalRetriever = app.state.retriever
        amendment_map: Dict[str, Any] = app.state.amendment_map
        history_db: QueryHistoryDB = app.state.history_db

        raw_results = retriever.search(
            query=payload.query,
            top_k=payload.top_k,
            alpha=payload.alpha
        )

        results = [enrich_result(r, amendment_map) for r in raw_results]

        history_db.insert_history(
            api_type="hybrid",
            original_query=payload.query,
            processed_query=None,
            top_k=payload.top_k,
            results=results
        )

        return SearchResponse(
            success=True,
            api_type="hybrid",
            original_query=payload.query,
            processed_query=None,
            top_k=payload.top_k,
            results=results
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hybrid search: {str(e)}")


@app.post("/search/llm", response_model=SearchResponse)
def search_llm(payload: LLMSearchRequest):
    try:
        retriever: LegalRetriever = app.state.retriever
        llm_engine: GeminiQueryProcessor = app.state.llm_engine
        amendment_map: Dict[str, Any] = app.state.amendment_map
        history_db: QueryHistoryDB = app.state.history_db

        refined_data = llm_engine.rewrite(payload.query)
        refined_query = refined_data.get("rewritten_query", payload.query)
        vehicle_type = refined_data.get("vehicle_type")
        expand_queries = refined_data.get("expand_query", [refined_query])

        # Search nhiều candidate để LLM chọn
        all_results = []
        for eq in expand_queries:
            res = retriever.search(
                eq,
                top_k=10,
                alpha=payload.alpha,
                vehicle_type=vehicle_type
            )
            all_results.extend(res)

        # Remove duplicates, giữ score tốt nhất
        unique_results = {}
        for res in all_results:
            vid = res["violation_id"]
            if vid not in unique_results or res["scores"]["hybrid"] > unique_results[vid]["scores"]["hybrid"]:
                unique_results[vid] = res

        candidate_results = list(unique_results.values())
        candidate_results.sort(key=lambda x: x["scores"]["hybrid"], reverse=True)
        candidate_results = candidate_results[:10]

        # LLM chọn best
        best_result = None
        if candidate_results:
            best_result = llm_engine.select_best_result(payload.query, candidate_results)

            if best_result:
                best_result = enrich_result(best_result, amendment_map)

        # Lưu history: chỉ lưu best_result cho gọn
        history_db.insert_history(
            api_type="llm",
            original_query=payload.query,
            processed_query=refined_query,
            top_k=1 if best_result else 0,
            results=[best_result] if best_result else []
        )

        return SearchResponse(
            success=True,
            api_type="llm",
            original_query=payload.query,
            processed_query=refined_query,
            vehicle_type=vehicle_type,
            expand_queries=expand_queries,
            top_k=1 if best_result else 0,
            results=None,
            best_result=best_result
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi llm search: {str(e)}")


@app.get("/history", response_model=HistoryResponse)
def get_all_history(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    try:
        history_db: QueryHistoryDB = app.state.history_db
        items = history_db.get_history(limit=limit, offset=offset)

        return HistoryResponse(
            success=True,
            total=len(items),
            items=items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy lịch sử: {str(e)}")


@app.get("/history/hybrid", response_model=HistoryResponse)
def get_hybrid_history(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    try:
        history_db: QueryHistoryDB = app.state.history_db
        items = history_db.get_history(api_type="hybrid", limit=limit, offset=offset)

        return HistoryResponse(
            success=True,
            total=len(items),
            items=items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy lịch sử hybrid: {str(e)}")


@app.get("/history/llm", response_model=HistoryResponse)
def get_llm_history(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    try:
        history_db: QueryHistoryDB = app.state.history_db
        items = history_db.get_history(api_type="llm", limit=limit, offset=offset)

        return HistoryResponse(
            success=True,
            total=len(items),
            items=items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy lịch sử llm: {str(e)}")


@app.get("/history/{history_id}")
def get_history_detail(history_id: int):
    try:
        history_db: QueryHistoryDB = app.state.history_db
        item = history_db.get_by_id(history_id)

        if not item:
            raise HTTPException(status_code=404, detail="Không tìm thấy lịch sử truy vấn")

        return {
            "success": True,
            "item": item
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy chi tiết lịch sử: {str(e)}")
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)