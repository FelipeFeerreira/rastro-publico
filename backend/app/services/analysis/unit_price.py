"""Cálculo validado de preço unitário.

Regra: unit_price = total / quantidade, sempre com validação prévia de
quantidade, unidade de medida e moeda. Nunca calcular sobre dados inválidos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_UNIDADES_VALIDAS = {
    "unidade", "un", "und", "peca", "caixa", "cx", "pacote", "pct", "kg", "g",
    "litro", "l", "ml", "metro", "m", "m2", "m3", "hora", "h", "dia", "mes",
    "servico", "global", "verba", "tonelada", "t", "frasco", "ampola", "comprimido",
    "resma", "rolo", "garrafa", "saco", "duzia", "pecas", "milheiro",
}


@dataclass
class UnitPriceResult:
    unit_price: Decimal | None
    is_valid: bool
    issues: list[str] = field(default_factory=list)

    @property
    def reason(self) -> str:
        return "; ".join(self.issues) if self.issues else "ok"


def normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    return unit.strip().lower().replace("²", "2").replace("³", "3")


def compute_unit_price(
    total: Decimal | float | None,
    quantity: Decimal | float | None,
    unit: str | None = None,
) -> UnitPriceResult:
    issues: list[str] = []

    if total is None or quantity is None:
        return UnitPriceResult(None, False, ["valor total ou quantidade ausente"])

    try:
        total_d = Decimal(str(total))
        quantity_d = Decimal(str(quantity))
    except (InvalidOperation, ValueError):
        return UnitPriceResult(None, False, ["valor não numérico"])

    if quantity_d <= 0:
        issues.append("quantidade deve ser maior que zero")
    if total_d < 0:
        issues.append("valor total negativo")
    if total_d == 0:
        issues.append("valor total zerado (possível item não homologado)")

    normalized_unit = normalize_unit(unit)
    if normalized_unit is None:
        issues.append("unidade de medida ausente")
    elif normalized_unit not in _UNIDADES_VALIDAS:
        issues.append(f"unidade de medida incomum: '{unit}'")

    if quantity_d <= 0:
        return UnitPriceResult(None, False, issues)

    unit_price = (total_d / quantity_d).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    # Um preço unitário válido precisa ser finito e não negativo.
    if unit_price < 0:
        issues.append("preço unitário negativo")
        return UnitPriceResult(None, False, issues)

    is_valid = quantity_d > 0 and total_d >= 0
    return UnitPriceResult(unit_price, is_valid, issues)
