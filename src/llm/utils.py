from ..kg.vector_index import build_index, search
from ..llm.promts import ANSWER_PROMPT
from langchain_core.prompts import ChatPromptTemplate
import json
from ..llm.client import get_llm_client
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from ..kg.vector_index import MODEL_NAME, INDEX_FILE, META_FILE
# Ouput parser for the LLM answer
class LLMAnswerOutputParser(BaseModel):
    answer: str


# TODO: LOAD FROM KG PAKEG
SEARCH_INDEX = build_index()     
MODEL = SentenceTransformer(MODEL_NAME)
INDEX = faiss.read_index(str(INDEX_FILE))


def search(query: str, top_k: int = 5):
    
    with META_FILE.open("r", encoding="utf-8") as f:
        meta = json.load(f)

    q_emb = MODEL.encode([query], normalize_embeddings=True)
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
