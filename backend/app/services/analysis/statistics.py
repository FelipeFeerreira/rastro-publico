"""Estatística robusta usada nas comparações de preço.

Métodos escolhidos por resistência a valores extremos: mediana, intervalos
interquartis e escore z modificado (MAD). Nenhum resultado constitui prova de
irregularidade; são indicadores para verificação humana.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


def _to_float(values: list[Decimal | float | int]) -> list[float]:
    return [float(v) for v in values if v is not None]


def median(values: list[Decimal | float | int]) -> float | None:
    data = sorted(_to_float(values))
    if not data:
        return None
    n = len(data)
    mid = n // 2
    if n % 2:
        return data[mid]
    return (data[mid - 1] + data[mid]) / 2.0


def percentile(values: list[Decimal | float | int], p: float) -> float | None:
    """Percentil com interpolação linear (método 7 de Hyndman-Fan)."""
    data = sorted(_to_float(values))
    if not data:
        return None
    if not 0 <= p <= 100:
        raise ValueError("percentil deve estar entre 0 e 100")
    if len(data) == 1:
        return data[0]
    rank = (p / 100.0) * (len(data) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(data) - 1)
    fraction = rank - lower
    return data[lower] + (data[upper] - data[lower]) * fraction


def iqr(values: list[Decimal | float | int]) -> float | None:
    q1 = percentile(values, 25)
    q3 = percentile(values, 75)
    if q1 is None or q3 is None:
        return None
    return q3 - q1


def mad(values: list[Decimal | float | int]) -> float | None:
    med = median(values)
    if med is None:
        return None
    return median([abs(float(v) - med) for v in values])


def modified_zscore(value: float, values: list[Decimal | float | int]) -> float | None:
    """Escore z modificado (0.6745 * (x - mediana) / MAD). Robusto a outliers."""
    med = median(values)
    deviation = mad(values)
    if med is None or deviation in (None, 0):
        return None
    return 0.6745 * (value - med) / deviation


def round_money(value: float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class Distribution:
    count: int
    median: float | None
    p25: float | None
    p75: float | None
    minimum: float | None
    maximum: float | None

    @classmethod
    def from_values(cls, values: list[Decimal | float | int]) -> Distribution:
        data = _to_float(values)
        return cls(
            count=len(data),
            median=median(data),
            p25=percentile(data, 25),
            p75=percentile(data, 75),
            minimum=min(data) if data else None,
            maximum=max(data) if data else None,
        )

    @property
    def iqr(self) -> float | None:
        if self.p25 is None or self.p75 is None:
            return None
        return self.p75 - self.p25
