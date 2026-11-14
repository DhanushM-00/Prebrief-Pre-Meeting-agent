"""Research agent chat — evidence-grounded answers for a research session."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import AnonymousSessionId
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_agent import answer_question

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, response_model_by_alias=True)
async def post_chat(
    req: ChatRequest,
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Answer a question using findings from a research session owned by the caller.

    The agent never fabricates facts. If the session is missing or the answer is
    not supported by collected evidence, it says so explicitly.
    """
    return answer_question(
        db=db,
        owner_session_id=session_id,
        question=req.question,
        research_session_id=req.research_session_id,
        entity_name=req.entity_name,
    )
