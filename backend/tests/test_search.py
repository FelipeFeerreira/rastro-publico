from app.services.search import SearchService
from tests.fixtures import create_computer_dataset


def test_search_finds_procurements_by_text(db):
    create_computer_dataset(db)
    results = SearchService(db).search("computadores desktop")
    types = {g.type for g in results.groups}
    assert "procurement" in types
    assert results.total >= 6


def test_search_filters_by_year(db):
    create_computer_dataset(db)
    results = SearchService(db).search("computadores", year=2026, types=["procurement"])
    assert results.total >= 6
    empty = SearchService(db).search("computadores", year=1999, types=["procurement"])
    assert empty.total == 0


def test_suggest_returns_municipality(db):
    create_computer_dataset(db)
    suggestions = SearchService(db).suggest("Camp")
    assert any(s["type"] == "municipality" and s["label"] == "Campinas" for s in suggestions)


def test_empty_query_returns_nothing(db):
    results = SearchService(db).search("")
    assert results.total == 0
