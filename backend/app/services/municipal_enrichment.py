"""Correspondência confiável entre despesas municipais e o CSV oficial do TCE-SP.

A chave natural é construída a partir de campos presentes nas DUAS fontes
(API de eventos e CSV de detalhes), normalizados. Nunca "chutamos" o id do
detalhe: só usamos o `id_despesa_detalhe` do CSV quando a chave casa de forma
inequívoca (1:1). Em caso de dúvida, o registro é marcado como ambíguo.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.connectors.tce_sp import TceSpConnector
from app.services import normalization as norm

_SPACE = re.compile(r"\s+")


def match_key(
    *,
    ano: Any,
    orgao: Any,
    mes: Any,
    evento: Any,
    nr_empenho: Any,
    identificador: Any,
    dt_emissao: Any,
    vl_despesa: Any,
) -> str:
    stage = TceSpConnector.map_stage(str(evento) if evento is not None else None)
    nr = _SPACE.sub("", str(nr_empenho or ""))
    date = norm.parse_br_date(dt_emissao)
    value = norm.parse_decimal(vl_despesa)
    parts = [
        str(ano or ""),
        norm.normalize_text(str(orgao) if orgao is not None else None),
        str(TceSpConnector.month_name_to_number(str(mes) if mes is not None else None) or ""),
        stage.value if stage else norm.normalize_text(str(evento) if evento is not None else None),
        nr,
        norm.only_digits(str(identificador) if identificador is not None else None),
        date.isoformat() if date else "",
        str(value) if value is not None else "",
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def key_from_csv_row(row: dict[str, Any]) -> str:
    return match_key(
        ano=row.get("ano_exercicio"),
        orgao=row.get("ds_orgao"),
        mes=row.get("mes_ref_extenso"),
        evento=row.get("tp_despesa"),
        nr_empenho=row.get("nr_empenho"),
        identificador=row.get("identificador_despesa"),
        dt_emissao=row.get("dt_emissao_despesa"),
        vl_despesa=row.get("vl_despesa"),
    )


def key_from_expense(expense: Any, orgao_name: str | None) -> str:
    stage = expense.stage
    evento = stage.value if hasattr(stage, "value") else stage
    return match_key(
        ano=expense.event_year,
        orgao=orgao_name,
        mes=expense.month_name,
        evento=evento,
        nr_empenho=expense.empenho_number,
        identificador=expense.supplier_raw_id,
        dt_emissao=expense.event_date,
        vl_despesa=expense.value,
    )
