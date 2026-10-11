"""Testes da importação de contratos do Comprasnet (IFSP Campus Salto / UASG 158364).

Fixtures com a MESMA ESTRUTURA das respostas reais verificadas em
https://contratos.comprasnet.gov.br/api/contrato/ug/158364 (valores rotulados).
Nenhum dado de governo é fabricado para produção: aqui são fixtures de teste.
"""

from __future__ import annotations

import httpx
import respx

from app.services.ingestion import IngestionService

BASE = "https://contratos.comprasnet.gov.br"
SALTO_UASG = "158364"
OTHER_UASG = "158154"  # outra unidade do mesmo órgão 26439
ORG_CODE = "26439"


def make_record(
    contract_id: int,
    *,
    uasg: str = SALTO_UASG,
    situacao: str = "Ativo",
    **overrides,
) -> dict:
    record = {
        "id": contract_id,
        "receita_despesa": "Despesa",
        "numero": f"{contract_id % 100000:05d}/2021",
        "contratante": {
            "orgao": {
                "codigo": ORG_CODE,
                "nome": "INST.FED.DE EDUC.,CIENC.E TEC.DE SAO PAULO",
                "unidade_gestora": {
                    "codigo": uasg,
                    "nome": "IFSP - CAMPUS SALTO",
                    "nome_resumido": "IFSP SALTO",
                    "sisg": "Sim",
                    "utiliza_siafi": "Sim",
                },
            },
            "orgao_origem": {"codigo": ORG_CODE},
        },
        "fornecedor": {
            "cnpj_cpf_idgener": "09.177.971/0001-86",
            "nome": "AUE PROVEDOR DE INTERNET LTDA",
            "tipo": "JURIDICA",
        },
        "tipo": "Contrato",
        "situacao": situacao,
        "processo": "23313.000296/2018-78",
        "objeto": "SERVIÇO TELEFÔNICO FIXO COMUTADO (STFC) LOCAL E LONGA DISTÂNCIA",
        "data_assinatura": "2018-08-13",
        "data_publicacao": "2021-01-15",
        "vigencia_inicio": "2018-08-13",
        "vigencia_fim": "2023-08-12",
        "valor_inicial": "19.045,32",
        "valor_global": "19.045,32",
        "valor_acumulado": "38.090,64",
        "unidade_compra": uasg,
    }
    record.update(overrides)
    return record


def _mock_unit(active: list[dict], inactive: list[dict], uasg: str = SALTO_UASG) -> None:
    respx.get(f"{BASE}/api/contrato/ug/{uasg}").mock(
        return_value=httpx.Response(200, json=active)
    )
    respx.get(f"{BASE}/api/contrato/inativo/ug/{uasg}").mock(
        return_value=httpx.Response(200, json=inactive)
    )


SALTO_ARGS = {
    "municipality_ibge": "3545209",
    "municipality_name": "Salto",
    "uf": "SP",
}


@respx.mock
def test_import_active_and_inactive_records(db):
    _mock_unit(
        [make_record(83385, situacao="Ativo")],
        [make_record(14086, situacao="Inativo")],
    )
    run = IngestionService(db).ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)

    assert run.records_fetched == 2
    assert run.records_inserted == 2
    assert run.status.value == "success"

    from sqlalchemy import select

    from app.models.geo import GovernmentEntity, Municipality
    from app.models.procurement import Contract
    from app.models.supplier import Supplier

    contracts = list(db.scalars(select(Contract).order_by(Contract.external_id)))
    assert {c.external_id for c in contracts} == {"83385", "14086"}
    active = next(c for c in contracts if c.external_id == "83385")
    assert active.source_system == "comprasnet"
    assert active.uasg == SALTO_UASG
    assert active.organization_code == ORG_CODE
    assert active.number == "83385/2021"
    assert active.contract_type == "Contrato"
    assert float(active.initial_value) == 19045.32
    assert float(active.global_value) == 19045.32
    assert float(active.accumulated_value) == 38090.64
    assert active.status.value == "vigente"
    assert active.source_url == f"{BASE}/api/contrato/id/83385"
    assert active.collected_at is not None

    inactive = next(c for c in contracts if c.external_id == "14086")
    assert inactive.status.value == "encerrado"

    entity = db.scalar(select(GovernmentEntity).where(GovernmentEntity.uasg == SALTO_UASG))
    assert entity is not None
    assert entity.sphere.value == "federal"
    assert entity.name == "IFSP - CAMPUS SALTO"
    muni = db.scalar(select(Municipality).where(Municipality.ibge_code == "3545209"))
    assert muni is not None and entity.municipality_id == muni.id

    supplier = db.scalar(select(Supplier).where(Supplier.name == "AUE PROVEDOR DE INTERNET LTDA"))
    assert supplier is not None and supplier.document == "09177971000186"
    # Comprasnet envia "JURIDICA"; deve ser normalizado para o canônico "PJ".
    assert supplier.document_type == "PJ"


@respx.mock
def test_rejects_contracts_from_other_uasg(db):
    """Contrato de outra unidade do mesmo órgão não pode ser atribuído a Salto."""
    _mock_unit(
        [make_record(1, uasg=OTHER_UASG), make_record(2, uasg=SALTO_UASG)],
        [],
    )
    run = IngestionService(db).ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)

    assert run.records_inserted == 1
    assert run.error_count == 1
    assert run.status.value == "partial"

    from sqlalchemy import select

    from app.models.procurement import Contract

    contracts = list(db.scalars(select(Contract)))
    assert [c.external_id for c in contracts] == ["2"]


@respx.mock
def test_reimport_is_idempotent(db):
    _mock_unit([make_record(83385)], [])
    service = IngestionService(db)

    first = service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    second = service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)

    assert first.records_inserted == 1
    assert second.records_inserted == 0
    assert second.records_updated == 1

    from sqlalchemy import func, select

    from app.models.procurement import Contract

    total = db.scalar(select(func.count()).select_from(Contract))
    assert total == 1


@respx.mock
def test_missing_values_stay_null(db):
    _mock_unit(
        [
            make_record(
                999,
                valor_inicial=None,
                valor_global=None,
                valor_acumulado=None,
                data_assinatura=None,
                vigencia_inicio=None,
                vigencia_fim=None,
                data_publicacao=None,
            )
        ],
        [],
    )
    IngestionService(db).ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)

    from sqlalchemy import select

    from app.models.procurement import Contract

    contract = db.scalar(select(Contract))
    assert contract is not None
    assert contract.initial_value is None
    assert contract.global_value is None
    assert contract.accumulated_value is None
    assert contract.signed_at is None
    assert contract.effective_until is None


@respx.mock
def test_source_failure_marks_run_failed(db):
    respx.get(f"{BASE}/api/contrato/ug/{SALTO_UASG}").mock(
        return_value=httpx.Response(500, text="erro interno")
    )
    run = IngestionService(db).ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    assert run.status.value == "failed"
    assert run.error_count >= 1


@respx.mock
def test_unknown_unit_returns_empty_success(db):
    respx.get(f"{BASE}/api/contrato/ug/{SALTO_UASG}").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    respx.get(f"{BASE}/api/contrato/inativo/ug/{SALTO_UASG}").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    run = IngestionService(db).ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    assert run.status.value == "success"
    assert run.records_fetched == 0
    assert run.records_inserted == 0


@respx.mock
def test_api_filters_by_uasg(db, client):
    """A filtragem por UASG isola o campus federal de outras unidades."""
    _mock_unit([make_record(83385)], [], uasg=SALTO_UASG)
    _mock_unit([make_record(1, uasg=OTHER_UASG)], [], uasg=OTHER_UASG)

    service = IngestionService(db)
    service.ingest_comprasnet_contracts(SALTO_UASG, **SALTO_ARGS)
    service.ingest_comprasnet_contracts(OTHER_UASG, **SALTO_ARGS)

    response = client.get("/api/v1/contratos", params={"uasg": SALTO_UASG})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["external_id"] == "83385"
    assert body["items"][0]["source_system"] == "comprasnet"
    assert body["items"][0]["entity"]["sphere"] == "federal"

    by_system = client.get("/api/v1/contratos", params={"source_system": "comprasnet"})
    assert by_system.json()["total"] == 2
