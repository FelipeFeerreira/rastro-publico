"""Testes de execução financeira (empenhos/faturas) do Comprasnet.

Garantem que valor contratado NÃO é exibido como pago, que estágios ficam
separados, que a importação é idempotente e que a API filtra por UASG.
"""

from __future__ import annotations

import httpx
import respx
from sqlalchemy import select

from app.models.procurement import Contract, Payment
from app.services.ingestion import IngestionService
from tests.test_comprasnet import BASE, SALTO_ARGS, SALTO_UASG, _mock_unit, make_record

CONTRACT_ID = 83385


def make_empenho(emp_id: int, *, pago="1.567,43", liquidado="0,00", empenhado="1.567,43") -> dict:
    return {
        "id": emp_id,
        "unidade_gestora": SALTO_UASG,
        "gestao": "26439",
        "numero": "2023NE000012",
        "data_emissao": "2023-02-14",
        "credor": "09.177.971/0001-86 - AUE PROVEDOR DE INTERNET LTDA",
        "naturezadespesa": "339039 - OUTROS SERVICOS DE TERCEIROS",
        "empenhado": empenhado,
        "liquidado": liquidado,
        "pago": pago,
        "links": {
            "documento_pagamento": "https://sta.api.gov.br/api/ordembancaria/empenho/158364264392023NE000012"
        },
        "credor_obj": {
            "tipo": "JURIDICA",
            "cnpj_cpf_idgener": "09.177.971/0001-86",
            "nome": "AUE PROVEDOR DE INTERNET LTDA",
        },
    }


def make_fatura(fat_id: int, *, liquidacao="2024-08-01", valor="474,31") -> dict:
    return {
        "id": fat_id,
        "numero": "1876723",
        "tipo_instrumento_cobranca": "Nota Fiscal",
        "fornecedor_contrato": "09.177.971/0001-86",
        "emissao": "2024-07-05",
        "vencimento": "2024-07-19",
        "valor": valor,
        "valorliquido": valor,
        "data_liquidacao": liquidacao,
    }


def _mock_contract_and_financials(empenhos, faturas):
    _mock_unit([make_record(CONTRACT_ID)], [])
    respx.get(f"{BASE}/api/contrato/{CONTRACT_ID}/empenhos").mock(
        return_value=httpx.Response(200, json=empenhos)
    )
    respx.get(f"{BASE}/api/contrato/{CONTRACT_ID}/faturas").mock(
        return_value=httpx.Response(200, json=faturas)
    )


@respx.mock
def test_imports_stages_separately(db):
    _mock_contract_and_financials(
        [make_empenho(10145339, empenhado="1.567,43", liquidado="1.000,00", pago="500,00")],
        [],
    )
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    run = service.ingest_comprasnet_payments(SALTO_UASG)

    assert run.records_fetched == 1
    payments = list(db.scalars(select(Payment).order_by(Payment.stage)))
    stages = {p.stage.value: float(p.value) for p in payments}
    assert stages == {"empenhado": 1567.43, "liquidado": 1000.0, "pago": 500.0}
    assert all(p.source_system == "comprasnet" for p in payments)
    assert all("empenho:" in (p.external_id or "") for p in payments)


@respx.mock
def test_contracted_value_is_not_paid(db):
    """O valor global do contrato não pode aparecer como pago."""
    _mock_contract_and_financials(
        [make_empenho(1, empenhado="1.000,00", liquidado="0,00", pago="0,00")],
        [],
    )
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    service.ingest_comprasnet_payments(SALTO_UASG)

    contract = db.scalar(select(Contract))
    paid = db.scalar(
        select(Payment).where(Payment.contract_id == contract.id, Payment.stage == "pago")
    )
    assert paid is not None and float(paid.value) == 0.0
    assert float(contract.global_value) == 19045.32  # contratado ≠ pago


@respx.mock
def test_pending_invoice_is_not_imported_as_payment(db):
    _mock_contract_and_financials([], [make_fatura(346512, liquidacao=None)])
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    service.ingest_comprasnet_payments(SALTO_UASG)
    assert list(db.scalars(select(Payment))) == []


@respx.mock
def test_liquidated_invoice_is_imported(db):
    _mock_contract_and_financials([], [make_fatura(999, liquidacao="2024-08-01", valor="474,31")])
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    service.ingest_comprasnet_payments(SALTO_UASG)
    payments = list(db.scalars(select(Payment)))
    assert len(payments) == 1
    assert payments[0].stage.value == "liquidado"
    assert float(payments[0].value) == 474.31
    assert payments[0].reference_date.isoformat() == "2024-08-01"


@respx.mock
def test_payment_import_is_idempotent(db):
    _mock_contract_and_financials([make_empenho(1)], [])
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    first = service.ingest_comprasnet_payments(SALTO_UASG)
    second = service.ingest_comprasnet_payments(SALTO_UASG)
    # empenhado, liquidado e pago são gravados (0,00 é valor explícito, não ausente).
    assert first.records_inserted == 3
    assert second.records_inserted == 0
    assert second.records_updated >= 1


@respx.mock
def test_api_exposes_payments_and_summary(db, client):
    _mock_contract_and_financials(
        [make_empenho(1, empenhado="1.000,00", liquidado="0,00", pago="250,00")],
        [],
    )
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    service.ingest_comprasnet_payments(SALTO_UASG)

    contract = db.scalar(select(Contract))
    listing = client.get(f"/api/v1/contratos/{contract.id}/pagamentos")
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    detail = client.get(f"/api/v1/contratos/{contract.id}")
    summary = detail.json()["payment_summary"]
    assert float(summary["empenhado"]) == 1000.0
    assert float(summary["pago"]) == 250.0

    by_uasg = client.get("/api/v1/pagamentos", params={"uasg": SALTO_UASG})
    assert by_uasg.status_code == 200
    assert by_uasg.json()["total"] >= 1


@respx.mock
def test_contract_without_financials_is_success_with_no_payments(db):
    _mock_unit([make_record(CONTRACT_ID)], [])
    respx.get(f"{BASE}/api/contrato/{CONTRACT_ID}/empenhos").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    respx.get(f"{BASE}/api/contrato/{CONTRACT_ID}/faturas").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    run = service.ingest_comprasnet_payments(SALTO_UASG)
    assert run.status.value == "success"
    assert run.records_inserted == 0
    assert list(db.scalars(select(Payment))) == []
