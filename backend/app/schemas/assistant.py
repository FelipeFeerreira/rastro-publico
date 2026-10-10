"""Schemas do assistente de pesquisa."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class SuggestionOut(BaseModel):
    type: str
    id: int
    label: str
    subtitle: str | None = None
    url: str | None = None


class SearchRequest(BaseModel):
    q: str = ""
    types: list[str] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)
    uf: str | None = None
    year: int | None = None
    modality: int | None = None
    min_value: float | None = None
    max_value: float | None = None
