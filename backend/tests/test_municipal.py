"""Testes de despesas municipais do TCE-SP (Salto/SP).

Fixtures com a MESMA ESTRUTURA das respostas reais verificadas em
https://transparencia.tce.sp.gov.br/api/json/despesas/salto/2025/1
(rotuladas; não são dados reais para produção).
"""

from __future__ import annotations

import httpx
import respx
from sqlalchemy import func, select

from app.models.geo import GovernmentEntity, Municipality
from app.models.municipal import MunicipalExpense
from app.models.procurement import Payment
from app.services.ingestion import IngestionService

BASE = "https://transparencia.tce.sp.gov.br"
SALTO_ARGS = {"ibge_code": "3545209", "uf": "SP", "municipality_name": "Salto"}


def make_despesa(
    *,
    orgao="PREFEITURA MUNICIPAL DE SALTO",
    evento="Empenhado",
    nr_empenho="123-2025",
    id_fornecedor="CNPJ - PESSOA JURÍDICA - 46634507000106",
    nm_fornecedor="FORNECEDOR EXEMPLO LTDA",
    dt_emissao_despesa="10/01/2025",
    vl_despesa="1.000,00",
    mes="Janeiro",
) -> dict:
    return {
        "orgao": orgao,
        "mes": mes,
        "evento": evento,
        "nr_empenho": nr_empenho,
        "id_fornecedor": id_fornecedor,
        "nm_fornecedor": nm_fornecedor,
        "dt_emissao_despesa": dt_emissao_despesa,
        "vl_despesa": vl_despesa,
    }


def _mock_month(records, ano=2025, mes=1):
    respx.get(f"{BASE}/api/json/despesas/salto/{ano}/{mes}").mock(
        return_value=httpx.Response(200, json=records)
    )


@respx.mock
def test_import_stores_events_and_institutions(db):
    _mock_month(
        [
            make_despesa(evento="Empenhado", vl_despesa="1.000,00"),
            make_despesa(evento="Valor Liquidado", vl_despesa="800,00"),
            make_despesa(evento="Valor Pago", vl_despesa="500,00"),
            make_despesa(evento="Anulação", vl_despesa="200,00"),
            make_despesa(
                orgao="CÂMARA MUNICIPAL DE SALTO",
                evento="Empenhado",
                nr_empenho="9-2025",
                vl_despesa="300,00",
            ),
        ]
    )
    run = IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )

    assert run.records_inserted == 5
    assert run.records_fetched == 5

    muni = db.scalar(select(Municipality).where(Municipality.ibge_code == "3545209"))
    assert muni is not None and muni.name == "Salto"

    stages = {
        e.stage.value
        for e in db.scalars(select(MunicipalExpense))
    }
    assert stages == {"empenhado", "liquidado", "pago", "anulacao"}

    # Instituições municipais distintas (Prefeitura e Câmara), nunca federais.
    entities = list(db.scalars(select(GovernmentEntity).where(GovernmentEntity.sphere == "municipal")))
    assert {e.name for e in entities} == {
        "PREFEITURA MUNICIPAL DE SALTO",
        "CÂMARA MUNICIPAL DE SALTO",
    }
    camara = next(e for e in entities if "CÂMARA" in e.name)
    assert camara.power.value == "legislative"

    # Valor em formato brasileiro foi convertido para decimal.
    paid = db.scalar(
        select(MunicipalExpense).where(MunicipalExpense.stage == "pago")
    )
    assert float(paid.value) == 500.0
    assert paid.event_date.isoformat() == "2025-01-10"
    assert paid.source_url.endswith("/despesas/salto/2025/1")


@respx.mock
def test_reimport_is_idempotent(db):
    _mock_month([make_despesa(), make_despesa(evento="Valor Pago", vl_despesa="400,00")])
    service = IngestionService(db)
    first = service.ingest_tce_sp_despesas("salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS)
    second = service.ingest_tce_sp_despesas("salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS)
    assert first.records_inserted == 2
    assert second.records_inserted == 0
    assert second.records_updated == 2
    assert int(db.scalar(select(func.count()).select_from(MunicipalExpense))) == 2


@respx.mock
def test_financial_totals_and_cancellation(db, client):
    _mock_month(
        [
            make_despesa(evento="Empenhado", vl_despesa="1.000,00"),
            make_despesa(orgao="CÂMARA MUNICIPAL DE SALTO", evento="Empenhado", nr_empenho="9-2025", vl_despesa="300,00"),
            make_despesa(evento="Anulação", vl_despesa="200,00"),
            make_despesa(evento="Valor Liquidado", vl_despesa="800,00"),
            make_despesa(evento="Valor Pago", vl_despesa="500,00"),
        ]
    )
    IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )

    resumo = client.get("/api/v1/despesas-municipais/resumo", params={"municipio_ibge": "3545209"})
    assert resumo.status_code == 200
    body = resumo.json()
    assert float(body["empenhado"]) == 1300.0
    assert float(body["anulacao"]) == 200.0
    assert float(body["liquidado"]) == 800.0
    assert float(body["pago"]) == 500.0
    # Empenhado líquido = empenhado + reforço − anulação (sem contagem dupla).
    assert float(body["committed_net"]) == 1100.0


@respx.mock
def test_municipality_and_entity_filtering(db, client):
    _mock_month(
        [
            make_despesa(evento="Empenhado"),
            make_despesa(orgao="CÂMARA MUNICIPAL DE SALTO", nr_empenho="9-2025"),
        ]
    )
    IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )

    all_rows = client.get("/api/v1/despesas-municipais", params={"municipio_ibge": "3545209"})
    assert all_rows.json()["total"] == 2

    other = client.get("/api/v1/despesas-municipais", params={"municipio_ibge": "9999999"})
    assert other.json()["total"] == 0

    camara = db.scalar(
        select(GovernmentEntity).where(GovernmentEntity.name.like("%CÂMARA%"))
    )
    by_entity = client.get(
        "/api/v1/despesas-municipais", params={"entity_id": camara.id}
    )
    assert by_entity.json()["total"] == 1

    by_stage = client.get(
        "/api/v1/despesas-municipais", params={"municipio_ibge": "3545209", "stage": "empenhado"}
    )
    assert by_stage.json()["total"] == 2
    assert by_stage.json()["items"][0]["entity_name"]


@respx.mock
def test_missing_fields_do_not_break(db):
    _mock_month(
        [
            make_despesa(orgao="", id_fornecedor="", nm_fornecedor="", vl_despesa="", dt_emissao_despesa=""),
        ]
    )
    run = IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )
    assert run.records_inserted == 1
    expense = db.scalar(select(MunicipalExpense))
    assert expense.value is None
    assert expense.entity_id is None
    assert expense.supplier_id is None
    assert expense.event_date is None


@respx.mock
def test_unknown_event_is_skipped(db):
    _mock_month([make_despesa(evento="Transferência"), make_despesa()])
    run = IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )
    assert run.records_fetched == 2
    assert run.records_inserted == 1
    assert run.records_skipped == 1


@respx.mock
def test_source_failure_marks_run_failed(db):
    respx.get(f"{BASE}/api/json/despesas/salto/2025/1").mock(
        return_value=httpx.Response(500, text="erro interno")
    )
    run = IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )
    assert run.status.value == "failed"
    assert run.error_count >= 1


@respx.mock
def test_municipal_kept_separate_from_federal(db):
    """Despesa municipal não cria pagamentos/contratos federais."""
    _mock_month([make_despesa(evento="Empenhado", vl_despesa="1.000,00")])
    IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )
    # Nenhum pagamento federal foi criado.
    assert int(db.scalar(select(func.count()).select_from(Payment))) == 0
    # A instituição é municipal (não federal).
    entity = db.scalar(select(GovernmentEntity))
    assert entity.sphere.value == "municipal"
    assert entity.uasg is None


@respx.mock
def test_summary_coverage_flags_partial_year(db, client):
    _mock_month([make_despesa(evento="Empenhado", nr_empenho="1-2025", dt_emissao_despesa="10/01/2025")], ano=2025, mes=1)
    _mock_month([make_despesa(evento="Empenhado", nr_empenho="1-2026", dt_emissao_despesa="10/01/2026")], ano=2026, mes=1)
    service = IngestionService(db)
    service.ingest_tce_sp_despesas("salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS)
    service.ingest_tce_sp_despesas("salto", year=2026, month_start=1, month_end=1, **SALTO_ARGS)

    resumo = client.get("/api/v1/despesas-municipais/resumo", params={"municipio_ibge": "3545209"})
    cov = resumo.json()["coverage"]
    assert set(cov["months_by_year"].keys()) == {"2025", "2026"}
    assert cov["months_by_year"]["2025"] == [1]
    # Ambos os anos têm menos de 12 meses => cobertura parcial explícita.
    assert set(cov["partial_years"]) == {2025, 2026}, cov
    assert cov["first_date"] is not None and cov["last_date"] is not None
    assert cov["last_collected_at"] is not None


@respx.mock
def test_institutions_breakdown_separates_stages(db, client):
    _mock_month(
        [
            make_despesa(orgao="PREFEITURA MUNICIPAL DE SALTO", evento="Empenhado", vl_despesa="1.000,00"),
            make_despesa(orgao="CÂMARA MUNICIPAL DE SALTO", evento="Empenhado", nr_empenho="9-2025", vl_despesa="300,00"),
            make_despesa(orgao="SERVICO AUTONOMO DE AGUA E ESGOTO DE SALTO - SAAE SALTO", evento="Valor Pago", nr_empenho="7-2025", vl_despesa="200,00"),
        ]
    )
    IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )

    resp = client.get("/api/v1/despesas-municipais/instituicoes", params={"municipio_ibge": "3545209"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    by_name = {i["entity_name"]: i for i in items}
    assert float(by_name["PREFEITURA MUNICIPAL DE SALTO"]["empenhado"]) == 1000.0
    assert float(by_name["CÂMARA MUNICIPAL DE SALTO"]["empenhado"]) == 300.0
    assert float(by_name["SERVICO AUTONOMO DE AGUA E ESGOTO DE SALTO - SAAE SALTO"]["pago"]) == 200.0
    # Ordenado por pago (maior primeiro): SAAE fica à frente.
    assert items[0]["entity_name"].startswith("SERVICO AUTONOMO")


@respx.mock
def test_individual_cpf_is_not_stored_or_exposed(db, client):
    _mock_month(
        [
            make_despesa(
                id_fornecedor="CPF - PESSOA FÍSICA - 123456",
                nm_fornecedor="MARIA DA SILVA",
                evento="Valor Pago",
                vl_despesa="150,00",
            )
        ]
    )
    IngestionService(db).ingest_tce_sp_despesas(
        "salto", year=2025, month_start=1, month_end=1, **SALTO_ARGS
    )
    expense = db.scalar(select(MunicipalExpense))
    assert expense.supplier_document is None
    assert expense.supplier_id is None
    assert expense.supplier_name == "MARIA DA SILVA"

    rows = client.get("/api/v1/despesas-municipais", params={"municipio_ibge": "3545209"}).json()
    assert rows["items"][0]["supplier_document"] is None
    assert rows["items"][0]["supplier_name"] == "MARIA DA SILVA"
