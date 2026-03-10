from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.llm.utils import llm_answer

router = APIRouter(prefix="/api")


class AnswerRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question about traffic law")
    top_k: int = Field(default=3, ge=1, le=20, description="Number of search results to use")
    conversation_history: str = Field(default="", description="Optional prior conversation for context")


class AnswerResponse(BaseModel):
    answer: str


@router.post("/answer", response_model=AnswerResponse)
async def answer(req: AnswerRequest) -> AnswerResponse:
    try:
        answer_text = llm_answer(
            user_query=req.query,
            top_k=req.top_k,
            conversation_history=req.conversation_history or "",
        )
        return AnswerResponse(answer=answer_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
