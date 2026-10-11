"""Classificação de preço em linguagem simples para o cidadão.

Não emite juízo de valor nem acusação. Apenas situa o preço em relação a compras
comparáveis, sempre que houver amostra confiável.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.analysis.reference import ComparableDataset

STATUS_INSIDE = "dentro_da_faixa"
STATUS_ABOVE = "acima_da_referencia"
STATUS_INSUFFICIENT = "sem_dados"

_ABOVE_RATIO = 1.3  # 30% acima da mediana já merece olhar


@dataclass
class PriceClassification:
    status: str
    label: str
    explanation: str
    percent_difference: float | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "label": self.label,
            "explanation": self.explanation,
            "percent_difference": self.percent_difference,
        }


def classify_price(value: float | None, dataset: ComparableDataset) -> PriceClassification:
    if value is None or not dataset.is_conclusive or dataset.distribution.median is None:
        return PriceClassification(
            status=STATUS_INSUFFICIENT,
            label="Sem dados suficientes para comparar",
            explanation=(
                "Não há compras comparáveis suficientes para dizer se este preço está "
                "dentro do esperado."
            ),
        )

    median = dataset.distribution.median
    p75 = dataset.distribution.p75
    diff = (value - median) / median * 100.0 if median else 0.0

    above_p75 = p75 is not None and value > p75
    if (above_p75 and value > median * _ABOVE_RATIO) or value > median * _ABOVE_RATIO:
        return PriceClassification(
            status=STATUS_ABOVE,
            label="Preço acima da referência",
            explanation=(
                f"Este preço está cerca de {diff:.0f}% acima da mediana de "
                f"{dataset.sample_size} compras comparáveis. Pode haver explicações "
                "legítimas (especificação, frete, prazo) — vale conferir os registros."
            ),
            percent_difference=round(diff, 1),
        )

    return PriceClassification(
        status=STATUS_INSIDE,
        label="Dentro da faixa de preços comparáveis",
        explanation=(
            f"Este preço está próximo da mediana de {dataset.sample_size} compras "
            "comparáveis e não chama atenção."
        ),
        percent_difference=round(diff, 1),
    )
