"""Testes do painel do campus (UASG) e da consistência financeira."""

from __future__ import annotations

import httpx
import respx
from sqlalchemy import select

from app.models.procurement import Contract
from app.services.ingestion import IngestionService
from tests.test_comprasnet import BASE, SALTO_ARGS, SALTO_UASG, _mock_unit, make_record
from tests.test_payments import make_empenho


def _setup_two_contracts():
    rec1 = make_record(1001, valor_global="10.000,00")
    rec2 = make_record(
        1002,
        valor_global="5.000,00",
        fornecedor={
            "cnpj_cpf_idgener": "11.222.333/0001-44",
            "nome": "OUTRA EMPRESA LTDA",
            "tipo": "JURIDICA",
        },
    )
    _mock_unit([rec1, rec2], [])
    respx.get(f"{BASE}/api/contrato/1001/empenhos").mock(
        return_value=httpx.Response(
            200, json=[make_empenho(1, empenhado="10.000,00", liquidado="0,00", pago="4.000,00")]
        )
    )
    respx.get(f"{BASE}/api/contrato/1002/empenhos").mock(
        return_value=httpx.Response(
            200, json=[make_empenho(2, empenhado="5.000,00", liquidado="0,00", pago="1.000,00")]
        )
    )


@respx.mock
def test_campus_dashboard_totals(db, client):
    _setup_two_contracts()
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    service.ingest_comprasnet_payments(SALTO_UASG)

    response = client.get(f"/api/v1/campus/{SALTO_UASG}")
    assert response.status_code == 200
    body = response.json()

    assert body["uasg"] == SALTO_UASG
    assert body["is_federal"] is True
    assert body["entity"]["name"] == "IFSP - CAMPUS SALTO"
    assert body["municipality_name"] == "Salto"

    totals = body["totals"]
    assert totals["contracts"] == 2
    assert totals["suppliers"] == 2

    fin = body["financials"]
    # Contratado = soma dos valores globais dos contratos.
    assert float(fin["contracted"]) == 15000.0
    # Estágios somados apenas dentro do próprio estágio.
    assert float(fin["committed"]) == 15000.0
    assert float(fin["liquidated"]) == 0.0
    assert float(fin["paid"]) == 5000.0
    # Contratado nunca é igual a pago por definição aqui.
    assert float(fin["contracted"]) != float(fin["paid"])


@respx.mock
def test_campus_unknown_uasg_is_404(client):
    response = client.get("/api/v1/campus/000000")
    assert response.status_code == 404


@respx.mock
def test_contracts_filter_by_uasg_and_value(db, client):
    _setup_two_contracts()
    IngestionService(db).ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)

    all_contracts = client.get("/api/v1/contratos", params={"uasg": SALTO_UASG})
    assert all_contracts.json()["total"] == 2

    # Outra UASG não retorna nada (filtro correto).
    other = client.get("/api/v1/contratos", params={"uasg": "999999"})
    assert other.json()["total"] == 0

    # Filtro por valor mínimo: apenas o contrato de 10.000.
    by_value = client.get(
        "/api/v1/contratos", params={"uasg": SALTO_UASG, "min_value": 8000}
    )
    items = by_value.json()["items"]
    assert len(items) == 1
    assert float(items[0]["global_value"]) == 10000.0

    # Filtro por fornecedor.
    supplier_id = items[0]["supplier"]["id"]
    by_supplier = client.get(
        "/api/v1/contratos", params={"uasg": SALTO_UASG, "supplier_id": supplier_id}
    )
    assert by_supplier.json()["total"] == 1


@respx.mock
def test_financial_totals_match_payment_rows(db):
    _setup_two_contracts()
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    service.ingest_comprasnet_payments(SALTO_UASG)

    # Soma direta dos lançamentos por estágio deve bater com o endpoint.
    from app.models.procurement import Payment

    committed = sum(
        float(p.value) for p in db.scalars(select(Payment).where(Payment.stage == "empenhado"))
    )
    paid = sum(
        float(p.value) for p in db.scalars(select(Payment).where(Payment.stage == "pago"))
    )
    assert committed == 15000.0
    assert paid == 5000.0
    assert db.scalar(select(Contract)) is not None
