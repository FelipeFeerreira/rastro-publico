"""Assistente de pesquisa com IA opcional e cálculos determinísticos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import rate_limit
from app.db.session import get_db
from app.schemas.assistant import AskRequest, SuggestionOut
from app.services.ai.assistant import GLOSSARY, ResearchAssistant
from app.services.search import SearchService

router = APIRouter(prefix="/assistente", tags=["Assistente de pesquisa"])


@router.post("/perguntar")
def ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(30, scope="assistant")),
) -> dict:
    answer = ResearchAssistant(db).answer(payload.question)
    return answer.to_dict()


@router.get("/glossario")
def glossary() -> dict:
    return {"termos": GLOSSARY}


@router.get("/glossario/{termo}")
def glossary_term(termo: str) -> dict:
    key = termo.strip().lower().replace(" ", "_")
    if key not in GLOSSARY:
        raise HTTPException(status_code=404, detail="Termo não encontrado no glossário.")
    return {"termo": key, "definicao": GLOSSARY[key]}


@router.get("/sugestoes", response_model=list[SuggestionOut])
def suggestions(q: str, db: Session = Depends(get_db)) -> list[dict]:
    return SearchService(db).suggest(q, limit=8)
