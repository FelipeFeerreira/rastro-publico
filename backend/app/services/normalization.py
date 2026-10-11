"""Normalização e padronização de dados brutos das fontes públicas.

Responsabilidades:
- limpar/acentuar texto para indexação e busca;
- converter valores monetários e datas de formatos brasileiros;
- mapear códigos de domínio do PNCP para os enums internos;
- derivar chaves de categoria para comparação de preços (heurística explícita).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.models.enums import (
    FinancialStage,  # noqa: F401  (reexportado para conveniência)
    ItemKind,
    ProcurementModality,
    ProcurementStatus,
)

_ACENTOS = re.compile(r"[\u0300-\u036f]")
_ESPACOS = re.compile(r"\s+")
_NAO_ALFANUM = re.compile(r"[^a-z0-9\s]")
_DIGITOS = re.compile(r"\D+")


def strip_accents(value: str) -> str:
    return _ACENTOS.sub("", unicodedata.normalize("NFD", value))


def normalize_text(value: str | None) -> str:
    """Minúsculas, sem acento, sem pontuação, espaços colapsados."""
    if not value:
        return ""
    text = strip_accents(value).lower()
    text = _NAO_ALFANUM.sub(" ", text)
    return _ESPACOS.sub(" ", text).strip()


def only_digits(value: str | None) -> str:
    return _DIGITOS.sub("", value or "")


def normalize_document(value: str | None) -> str | None:
    """Normaliza CNPJ/CPF para apenas dígitos; retorna None se inválido."""
    digits = only_digits(value)
    if len(digits) not in (11, 14):
        return None
    return digits


def normalize_document_type(value: str | None) -> str | None:
    """Padroniza o tipo de pessoa entre fontes (PJ/PF/PE).

    O PNCP usa `PJ`/`PF`/`PE`; o Comprasnet usa `JURIDICA`/`FISICA`/`ESTRANGEIRA`.
    """
    if not value:
        return None
    text = value.strip().upper()
    if text in ("PJ", "PF", "PE"):
        return text
    if text.startswith("JURID"):
        return "PJ"
    if text.startswith("FIS") or text.startswith("FÍS"):
        return "PF"
    if text.startswith("ESTRANG") or text.startswith("ESTRANJ"):
        return "PE"
    return text[:4] or None


def parse_decimal(value: object) -> Decimal | None:
    """Converte números vindos de JSON ou strings BR (R$ 1.234,56)."""
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if not text:
        return None
    # Formato brasileiro: 1.234,56 -> 1234.56
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_date(value: object) -> date | None:
    dt = parse_datetime(value)
    return dt.date() if dt else None


def parse_br_date(value: object) -> date | None:
    """Aceita datas no formato brasileiro (dd/mm/aaaa) ou ISO."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return parse_date(text)


_MODALITY_BY_CODE: dict[str, ProcurementModality] = {
    "1": ProcurementModality.LEILAO,
    "2": ProcurementModality.DIALOGO_COMPETITIVO,
    "3": ProcurementModality.CONCORRENCIA,
    "4": ProcurementModality.CONCURSO,
    "5": ProcurementModality.PREGAO,
    "6": ProcurementModality.DISPENSA,
    "7": ProcurementModality.INEXIGIBILIDADE,
    "8": ProcurementModality.MANIFESTACAO_INTERESSE,
    "9": ProcurementModality.PRE_QUALIFICACAO,
    "10": ProcurementModality.CREDENCIAMENTO,
    "11": ProcurementModality.LEILAO_ELETRONICO,
    "12": ProcurementModality.DIALOGO_COMPETITIVO_ELETRONICO,
    "13": ProcurementModality.CONCORRENCIA_ELETRONICA,
}


def map_modality(code: int | str | None) -> ProcurementModality:
    return _MODALITY_BY_CODE.get(str(code), ProcurementModality.DESCONHECIDA)


def map_procurement_status(name: str | None) -> ProcurementStatus:
    normalized = normalize_text(name)
    if "divulgada" in normalized:
        return ProcurementStatus.DIVULGADA
    if "revogad" in normalized:
        return ProcurementStatus.REVOGADA
    if "anulad" in normalized:
        return ProcurementStatus.ANULADA
    if "suspend" in normalized:
        return ProcurementStatus.SUSPENSA
    return ProcurementStatus.DESCONHECIDA


def map_item_kind(material_ou_servico: str | None, description: str | None = None) -> ItemKind:
    flag = (material_ou_servico or "").strip().upper()
    if flag.startswith("M"):
        return ItemKind.MATERIAL
    if flag.startswith("S"):
        return ItemKind.SERVICO
    if flag.startswith("O"):
        return ItemKind.OBRA
    text = normalize_text(description)
    if any(term in text for term in ("servico", "locacao", "mao de obra")):
        return ItemKind.SERVICO
    if any(term in text for term in ("obra", "construcao")):
        return ItemKind.OBRA
    return ItemKind.DESCONHECIDO


# --- Categorização heurística para comparação de preços ---
# Cada categoria possui termos-chave e uma unidade esperada. É uma heurística
# transparente e conservadora: itens só são comparados dentro da mesma chave.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("medicamento", ("medicamento", "remedio", "farmaco", "comprimido", "solucao oral")),
    ("material_escolar", ("material escolar", "caderno", "lapis", "caneta", "apostila")),
    ("informatica", ("computador", "notebook", "monitor", "desktop", "impressora", "tablet")),
    ("combustivel", ("combustivel", "gasolina", "diesel", "etanol", "arla")),
    ("alimentacao", ("alimento", "refeicao", "marmita", "cesta basica", "genero")),
    ("material_construcao", ("cimento", "areia", "brita", "tijolo", "argamassa", "manilha")),
    ("veiculo", ("veiculo", "automovel", "caminhonete", "ambulancia", "onibus")),
    ("mobiliario", ("cadeira", "mesa", "armario", "estante", "sofa")),
    ("limpeza", ("detergente", "sabao", "desinfetante", "agua sanitaria", "papel higienico")),
    ("servico_manutencao", ("manutencao", "reparo", "conservacao")),
    ("servico_ti", ("desenvolvimento de software", "licenca de software", "suporte tecnico")),
]


def derive_category_key(description: str | None, catalog_code: str | None = None) -> str:
    """Deriva uma chave de categoria estável para agrupar itens comparáveis.

    Prioriza o código de catálogo (CATMAT/CATSER) quando presente, pois é o
    identificador oficial do item. Caso contrário, aplica regras textuais.
    """
    if catalog_code:
        return f"cat:{only_digits(catalog_code) or catalog_code.strip()}"
    text = normalize_text(description)
    for key, terms in CATEGORY_RULES:
        if any(term in text for term in terms):
            return f"heur:{key}"
    # Fallback: primeiras palavras significativas.
    words = [w for w in text.split() if len(w) > 3][:4]
    return "txt:" + "_".join(words) if words else "txt:desconhecido"


def build_search_text(*parts: str | None) -> str:
    """Concatena campos relevantes para o índice de busca em texto completo."""
    seen: list[str] = []
    for part in parts:
        normalized = normalize_text(part)
        if normalized and normalized not in seen:
            seen.append(normalized)
    return " ".join(seen)
