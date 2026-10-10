"""Dados de referência estáveis (fontes oficiais catalogadas e UFs)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SourceStatus
from app.models.geo import State
from app.models.source import DataSource

# Unidades da Federação (código IBGE, sigla, nome).
STATES: list[tuple[str, str, str]] = [
    ("11", "RO", "Rondônia"), ("12", "AC", "Acre"), ("13", "AM", "Amazonas"),
    ("14", "RR", "Roraima"), ("15", "PA", "Pará"), ("16", "AP", "Amapá"),
    ("17", "TO", "Tocantins"), ("21", "MA", "Maranhão"), ("22", "PI", "Piauí"),
    ("23", "CE", "Ceará"), ("24", "RN", "Rio Grande do Norte"), ("25", "PB", "Paraíba"),
    ("26", "PE", "Pernambuco"), ("27", "AL", "Alagoas"), ("28", "SE", "Sergipe"),
    ("29", "BA", "Bahia"), ("31", "MG", "Minas Gerais"), ("32", "ES", "Espírito Santo"),
    ("33", "RJ", "Rio de Janeiro"), ("35", "SP", "São Paulo"), ("41", "PR", "Paraná"),
    ("42", "SC", "Santa Catarina"), ("43", "RS", "Rio Grande do Sul"),
    ("50", "MS", "Mato Grosso do Sul"), ("51", "MT", "Mato Grosso"),
    ("52", "GO", "Goiás"), ("53", "DF", "Distrito Federal"),
]

# Catálogo de fontes oficiais com URLs de documentação verificadas.
DATA_SOURCES: list[dict] = [
    {
        "code": "pncp",
        "name": "Portal Nacional de Contratações Públicas (PNCP)",
        "description": (
            "Base nacional de contratações públicas criada pela Lei 14.133/2021. "
            "Reúne editais, avisos, atas, contratos e resultados de União, estados "
            "e municípios."
        ),
        "homepage_url": "https://pncp.gov.br/",
        "api_documentation_url": "https://pncp.gov.br/api/consulta/swagger-ui/index.html",
        "license_name": "Dados Abertos Governamentais",
        "license_url": "https://pncp.gov.br/app/dados-abertos",
        "requires_authentication": False,
        "coverage_description": (
            "Cobertura nacional para contratações sob a Lei 14.133/2021. A "
            "qualidade e a completude dependem do envio pelos órgãos."
        ),
        "status": SourceStatus.ACTIVE,
    },
    {
        "code": "transparencia",
        "name": "Portal da Transparência do Governo Federal",
        "description": (
            "Dados de execução orçamentária e financeira, despesas, servidores e "
            "benefícios do Poder Executivo Federal."
        ),
        "homepage_url": "https://portaldatransparencia.gov.br/",
        "api_documentation_url": "https://api.portaldatransparencia.gov.br/swagger-ui/index.html",
        "license_name": "Licença de Dados Abertos",
        "license_url": "https://portaldatransparencia.gov.br/sobre",
        "requires_authentication": True,
        "coverage_description": "Poder Executivo Federal. Exige chave de API gratuita.",
        "status": SourceStatus.MAINTENANCE,
    },
    {
        "code": "camara",
        "name": "Dados Abertos da Câmara dos Deputados",
        "description": (
            "Despesas parlamentares (cota), proposições, votações e dados de "
            "deputados federais."
        ),
        "homepage_url": "https://dadosabertos.camara.leg.br/",
        "api_documentation_url": "https://dadosabertos.camara.leg.br/swagger/api.html",
        "license_name": "Open Data Commons Attribution",
        "license_url": "https://dadosabertos.camara.leg.br/",
        "requires_authentication": False,
        "coverage_description": "Câmara dos Deputados (âmbito federal legislativo).",
        "status": SourceStatus.MAINTENANCE,
    },
]


def seed_reference_data(db: Session) -> dict[str, int]:
    """Garante UFs e catálogo de fontes. Idempotente."""
    created = {"states": 0, "sources": 0}

    for ibge, uf, name in STATES:
        if db.scalar(select(State).where(State.uf == uf)) is None:
            db.add(State(ibge_code=ibge, uf=uf, name=name))
            created["states"] += 1

    for item in DATA_SOURCES:
        existing = db.scalar(select(DataSource).where(DataSource.code == item["code"]))
        if existing is None:
            db.add(DataSource(**item))
            created["sources"] += 1

    db.commit()
    return created


def get_source(db: Session, code: str) -> DataSource:
    source = db.scalar(select(DataSource).where(DataSource.code == code))
    if source is None:
        raise RuntimeError(
            f"Fonte '{code}' não cadastrada. Execute `python -m app.cli seed` primeiro."
        )
    return source
