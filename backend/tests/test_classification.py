"""Testes da classificação de preço em linguagem simples."""

from app.services.analysis.classification import (
    STATUS_ABOVE,
    STATUS_INSIDE,
    STATUS_INSUFFICIENT,
    classify_price,
)
from app.services.analysis.reference import ComparableDataset
from app.services.analysis.statistics import Distribution


def _dataset(prices: list[float]) -> ComparableDataset:
    return ComparableDataset(
        category_key="heur:informatica",
        unit="unidade",
        distribution=Distribution.from_values(prices),
        records=[{"unit_price": p} for p in prices],
    )


def test_insufficient_sample():
    result = classify_price(5000.0, _dataset([3000.0, 3100.0]))
    assert result.status == STATUS_INSUFFICIENT
    assert "Sem dados suficientes" in result.label


def test_price_inside_range():
    result = classify_price(3250.0, _dataset([3000.0, 3100.0, 3200.0, 3300.0, 3400.0]))
    assert result.status == STATUS_INSIDE
    assert result.label == "Dentro da faixa de preços comparáveis"


def test_price_above_reference():
    result = classify_price(12000.0, _dataset([3000.0, 3100.0, 3200.0, 3300.0, 3400.0]))
    assert result.status == STATUS_ABOVE
    assert result.label == "Preço acima da referência"
    assert result.percent_difference and result.percent_difference > 100


def test_none_value_is_insufficient():
    result = classify_price(None, _dataset([1, 2, 3, 4, 5]))
    assert result.status == STATUS_INSUFFICIENT
