from ..kg.vector_index import build_index, get_model, INDEX_FILE, META_FILE
from ..llm.promts import ANSWER_PROMPT
from langchain_core.prompts import ChatPromptTemplate
import json
from ..llm.client import get_llm_client
from pydantic import BaseModel
import faiss
import numpy as np

# Ouput parser for the LLM answer
class LLMAnswerOutputParser(BaseModel):
    answer: str


# Load existing index from disk (no rebuild on every run). Build only if missing.
if not INDEX_FILE.exists():
    build_index()
INDEX = faiss.read_index(str(INDEX_FILE))


def search(query: str, top_k: int = 5):
    model = get_model()
    with META_FILE.open("r", encoding="utf-8") as f:
        meta = json.load(f)

    q_emb = model.encode([query], normalize_embeddings=True)
    q_emb = np.array(q_emb, dtype="float32")

    scores, indices = INDEX.search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        results.append({
            "score": float(score),
            **meta[idx]
        })
    return results


def llm_answer(user_query: str, top_k: int = 3, conversation_history: str = "") -> str:
    rs = search(user_query, top_k=top_k)
    print("Found results: ", len(rs))
    if len(rs) == 0:
        return "Không tìm thấy kết quả phù hợp."
    prompts = ChatPromptTemplate.from_messages(
        [(item["role"], item["content"]) for item in ANSWER_PROMPT])
    prompt = prompts.invoke({
        "user_query": user_query,
        "legal_basis": json.dumps(rs, ensure_ascii=False, indent=2) ,
        "conversation_history": conversation_history,
    })
    llm = get_llm_client()
    # Bind the output parser to the LLM
    llm = llm.with_structured_output(LLMAnswerOutputParser)
    answer: LLMAnswerOutputParser = llm.invoke(prompt)
    return answer.answer
