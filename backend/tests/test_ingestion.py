"""Testes de ingestão com a API do PNCP simulada (sem rede real)."""

from __future__ import annotations

import httpx
import respx

from app.services.ingestion import IngestionService

SAMPLE_PUBLICATION = {
    "valorTotalHomologado": None,
    "orgaoEntidade": {
        "cnpj": "18629840000183",
        "razaoSocial": "MUNICIPIO DE POCOS DE CALDAS",
        "poderId": "N",
        "esferaId": "M",
    },
    "dataInclusao": "2026-01-01T06:43:42",
    "dataPublicacaoPncp": "2026-01-01T06:43:42",
    "dataAtualizacao": "2026-02-04T12:10:59",
    "anoCompra": 2025,
    "srp": True,
    "sequencialCompra": 251,
    "numeroCompra": "113",
    "processo": "234/2025",
    "numeroControlePNCP": "18629840000183-1-000251/2025",
    "objetoCompra": "FORNECIMENTO DE CIMENTO PORTLAND CP II-E-32",
    "valorTotalEstimado": 175000.0,
    "modalidadeId": 6,
    "modalidadeNome": "Pregão - Eletrônico",
    "modoDisputaNome": "Aberto-Fechado",
    "situacaoCompraNome": "Divulgada no PNCP",
    "unidadeOrgao": {
        "ufNome": "Minas Gerais",
        "ufSigla": "MG",
        "municipioNome": "Poços de Caldas",
        "codigoIbge": "3151800",
        "codigoUnidade": "5717",
        "nomeUnidade": "Prefeitura Municipal de Poços de Caldas",
    },
    "linkSistemaOrigem": "https://example.com/processo",
}

SAMPLE_ITEM = {
    "numeroItem": 1,
    "descricao": "CIMENTO PORTLAND CP II-E-32 SACO 50KG",
    "materialOuServico": "M",
    "valorUnitarioEstimado": 35.0,
    "valorTotal": 175000.0,
    "quantidade": 5000.0,
    "unidadeMedida": "Unidade",
    "criterioJulgamentoNome": "Menor preço",
    "situacaoCompraItemNome": "Homologado",
}

SAMPLE_RESULT = {
    "sequencialResultado": 1,
    "niFornecedor": "12345678000199",
    "nomeRazaoSocialFornecedor": "CIMENTOS BRASIL LTDA",
    "tipoPessoa": "PJ",
    "valorUnitarioHomologado": 34.5,
    "quantidadeHomologada": 5000.0,
    "valorTotalHomologado": 172500.0,
    "dataResultado": "2026-01-20",
    "situacaoCompraItemResultadoNome": "Homologado",
}


@respx.mock
def test_ingest_publication_creates_normalized_records(db):
    page = {
        "data": [SAMPLE_PUBLICATION],
        "totalRegistros": 1,
        "totalPaginas": 1,
        "numeroPagina": 1,
        "paginasRestantes": 0,
        "empty": False,
    }
    respx.get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao").mock(
        return_value=httpx.Response(200, json=page)
    )

    run = IngestionService(db).ingest_pncp_publications(
        "2026-01-01",
        "2026-01-07",
        modality_codes=[6],
        max_pages_per_modality=1,
    )

    assert run.records_inserted == 1
    assert run.status.value == "success"

    from sqlalchemy import select

    from app.models.geo import GovernmentEntity, Municipality
    from app.models.procurement import Procurement

    procurement = db.scalar(select(Procurement))
    assert procurement is not None
    assert procurement.pncp_control_number == "18629840000183-1-000251/2025"
    assert float(procurement.estimated_total) == 175000.0
    assert procurement.modality.value == "6"
    assert procurement.source_url.endswith("/2025/251")

    municipality = db.scalar(select(Municipality))
    assert municipality.ibge_code == "3151800"
    entity = db.scalar(select(GovernmentEntity))
    assert entity.name == "MUNICIPIO DE POCOS DE CALDAS"
    assert entity.sphere.value == "municipal"


@respx.mock
def test_ingest_is_idempotent(db):
    page = {
        "data": [SAMPLE_PUBLICATION],
        "totalRegistros": 1,
        "totalPaginas": 1,
        "numeroPagina": 1,
        "empty": False,
    }
    respx.get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao").mock(
        return_value=httpx.Response(200, json=page)
    )

    service = IngestionService(db)
    first = service.ingest_pncp_publications(
        "2026-01-01", "2026-01-07", modality_codes=[6], max_pages_per_modality=1
    )
    second = service.ingest_pncp_publications(
        "2026-01-01", "2026-01-07", modality_codes=[6], max_pages_per_modality=1
    )
    assert first.records_inserted == 1
    assert second.records_inserted == 0
    assert second.records_updated == 1


@respx.mock
def test_ingest_with_items(db):
    respx.get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [SAMPLE_PUBLICATION],
                "totalRegistros": 1,
                "totalPaginas": 1,
                "numeroPagina": 1,
            },
        )
    )
    respx.get(
        "https://pncp.gov.br/api/pncp/v1/orgaos/18629840000183/compras/2025/251/itens"
    ).mock(return_value=httpx.Response(200, json=[SAMPLE_ITEM]))
    respx.get(
        "https://pncp.gov.br/api/pncp/v1/orgaos/18629840000183/compras/2025/251"
        "/itens/1/resultados"
    ).mock(return_value=httpx.Response(200, json=[SAMPLE_RESULT]))

    IngestionService(db).ingest_pncp_publications(
        "2026-01-01", "2026-01-07", modality_codes=[6], max_pages_per_modality=1, with_items=True
    )

    from sqlalchemy import select

    from app.models.procurement import ProcurementItem, ProcurementResult
    from app.models.supplier import Supplier

    item = db.scalar(select(ProcurementItem))
    assert item is not None
    assert item.category_key == "heur:material_construcao"
    result = db.scalar(select(ProcurementResult))
    assert result is not None
    assert float(result.unit_price) == 34.5
    supplier = db.scalar(select(Supplier))
    assert supplier.document == "12345678000199"


@respx.mock
def test_ingest_handles_source_failure(db):
    respx.get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao").mock(
        return_value=httpx.Response(500, text="erro interno")
    )
    run = IngestionService(db).ingest_pncp_publications(
        "2026-01-01", "2026-01-07", modality_codes=[6], max_pages_per_modality=1
    )
    assert run.status.value == "failed"
    assert run.error_count >= 1
