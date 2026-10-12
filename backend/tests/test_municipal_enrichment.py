"""Testes do enriquecimento de despesas municipais com o CSV oficial do TCE-SP.

Fixtures com a MESMA ESTRUTURA do conjunto de dados real
(https://transparencia.tce.sp.gov.br/sites/default/files/csv/despesas-salto-2025.zip).
Nunca "chutamos" o id do detalhe: só casamos por chave natural 1:1.
"""

from __future__ import annotations

import csv
import io
import zipfile

import httpx
import respx
from sqlalchemy import select

from app.models.municipal import MunicipalExpense
from app.services.ingestion import IngestionService
from tests.test_municipal import BASE, SALTO_ARGS, _mock_month, make_despesa

CSV_HEADER = [
    "id_despesa_detalhe", "ano_exercicio", "ds_municipio", "ds_orgao", "mes_referencia",
    "mes_ref_extenso", "tp_despesa", "nr_empenho", "identificador_despesa", "ds_despesa",
    "dt_emissao_despesa", "vl_despesa", "ds_funcao_governo", "ds_subfuncao_governo",
    "cd_programa", "ds_programa", "cd_acao", "ds_acao", "ds_fonte_recurso",
    "ds_cd_aplicacao_fixo", "ds_modalidade_lic", "ds_elemento", "historico_despesa",
]

ZIP_URL = f"{BASE}/sites/default/files/csv/despesas-salto-2025.zip"


def csv_row(**overrides) -> dict:
    row = {
        "id_despesa_detalhe": "664111579",
        "ano_exercicio": "2025",
        "ds_municipio": "Salto",
        "ds_orgao": "PREFEITURA MUNICIPAL DE SALTO",
        "mes_referencia": "1",
        "mes_ref_extenso": "Janeiro",
        "tp_despesa": "Empenhado",
        "nr_empenho": " 123-2025",
        "identificador_despesa": "CNPJ - PESSOA JURÍDICA - 46634507000106",
        "ds_despesa": "FORNECEDOR EXEMPLO LTDA",
        "dt_emissao_despesa": "10/01/2025",
        "vl_despesa": "1000,00",
        "ds_funcao_governo": "ADMINISTRAÇÃO",
        "ds_subfuncao_governo": "ADMINISTRAÇÃO GERAL",
        "cd_programa": "1",
        "ds_programa": "Gestao Para Governar",
        "cd_acao": "2001",
        "ds_acao": "Manutencao geral das atividades do Gabinete",
        "ds_fonte_recurso": "TESOURO",
        "ds_cd_aplicacao_fixo": "0110 - GERAL",
        "ds_modalidade_lic": "OUTROS/NÃO APLICÁVEL",
        "ds_elemento": "31901101 - VENCIMENTOS E SALÁRIOS",
        "historico_despesa": "REF PGTO DE FERIAS",
    }
    row.update(overrides)
    return row


def make_csv_zip(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_HEADER, delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    content = buffer.getvalue().encode("latin-1")
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as archive:
        archive.writestr("despesas-salto-2025.csv", content)
    return zbuf.getvalue()


def _import_base_event(db):
    _mock_month([make_despesa(nr_empenho="123-2025", vl_despesa="1.000,00")], ano=2025, mes=1)
    IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )


@respx.mock
def test_enrichment_matches_and_stores_details(db):
    _import_base_event(db)
    respx.get(ZIP_URL).mock(return_value=httpx.Response(200, content=make_csv_zip([csv_row()])))

    run = IngestionService(db).enrich_tce_sp_expense_details(
        "salto", ibge_code="3545209", year=2025, limit=100
    )

    assert run.records_updated == 1
    expense = db.scalar(select(MunicipalExpense))
    assert expense.detail_id == "664111579"
    assert expense.detail_url.endswith("/despesas/detalhe/664111579")
    assert expense.history == "REF PGTO DE FERIAS"
    assert expense.activity_description == "Manutencao geral das atividades do Gabinete"
    assert expense.government_function == "ADMINISTRAÇÃO"
    assert expense.expense_element == "31901101 - VENCIMENTOS E SALÁRIOS"
    assert expense.enrichment_status == "enriched"
    assert expense.enriched_at is not None
    # Valores financeiros preservados (nunca alterados pelo enriquecimento).
    assert float(expense.value) == 1000.0


@respx.mock
def test_enrichment_missing_history_is_null_but_matched(db):
    _import_base_event(db)
    respx.get(ZIP_URL).mock(
        return_value=httpx.Response(
            200,
            content=make_csv_zip([csv_row(historico_despesa="", ds_acao="")]),
        )
    )
    IngestionService(db).enrich_tce_sp_expense_details(
        "salto", ibge_code="3545209", year=2025
    )
    expense = db.scalar(select(MunicipalExpense))
    assert expense.enrichment_status == "enriched"
    assert expense.history is None
    assert expense.activity_description is None
    # Ainda assim o link oficial existe (id presente no CSV).
    assert expense.detail_url is not None


@respx.mock
def test_enrichment_not_found_does_not_guess(db):
    _import_base_event(db)
    respx.get(ZIP_URL).mock(
        return_value=httpx.Response(200, content=make_csv_zip([csv_row(nr_empenho="999-2025")]))
    )
    run = IngestionService(db).enrich_tce_sp_expense_details(
        "salto", ibge_code="3545209", year=2025
    )
    expense = db.scalar(select(MunicipalExpense))
    assert run.records_updated == 0
    assert run.records_skipped == 1
    assert expense.enrichment_status == "not_found"
    assert expense.detail_id is None
    assert expense.detail_url is None


@respx.mock
def test_enrichment_ambiguous_is_flagged(db):
    _import_base_event(db)
    duplicate = [csv_row(id_despesa_detalhe="111"), csv_row(id_despesa_detalhe="222")]
    respx.get(ZIP_URL).mock(return_value=httpx.Response(200, content=make_csv_zip(duplicate)))
    run = IngestionService(db).enrich_tce_sp_expense_details(
        "salto", ibge_code="3545209", year=2025
    )
    expense = db.scalar(select(MunicipalExpense))
    assert expense.enrichment_status == "ambiguous"
    assert expense.detail_id is None
    assert run.error_count >= 1


@respx.mock
def test_enrichment_is_idempotent(db):
    _import_base_event(db)
    respx.get(ZIP_URL).mock(return_value=httpx.Response(200, content=make_csv_zip([csv_row()])))
    service = IngestionService(db)
    first = service.enrich_tce_sp_expense_details("salto", ibge_code="3545209", year=2025)
    second = service.enrich_tce_sp_expense_details("salto", ibge_code="3545209", year=2025)
    assert first.records_updated == 1
    assert second.records_fetched == 0  # nada pendente
    # force reenriquece
    third = service.enrich_tce_sp_expense_details(
        "salto", ibge_code="3545209", year=2025, force=True
    )
    assert third.records_updated == 1


@respx.mock
def test_enrichment_source_failure_marks_failed(db):
    _import_base_event(db)
    respx.get(ZIP_URL).mock(return_value=httpx.Response(500, text="erro"))
    run = IngestionService(db).enrich_tce_sp_expense_details(
        "salto", ibge_code="3545209", year=2025
    )
    assert run.status.value == "failed"
    assert run.error_count >= 1
    expense = db.scalar(select(MunicipalExpense))
    assert expense.enrichment_status is None  # não marcado como enriquecido
