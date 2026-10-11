"""Testes de servidores/remuneração do Portal da Transparência.

A API exige chave (TRANSPARENCIA_API_KEY). Sem chave, nada é importado e o
motivo é registrado de forma explícita. Com chave (simulada), validamos o
mapeamento e a verificação de campus (UORG).
"""

from __future__ import annotations

import httpx
import respx
from sqlalchemy import select

from app.core.config import settings
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.person import PublicPerson, Remuneration
from app.services import normalization as norm
from app.services.ingestion import IngestionService

PT_SERVIDORES = "https://api.portaldatransparencia.gov.br/api-de-dados/servidores"
ORG = "26439"
MES = "202501"


def _seed_campus(db) -> GovernmentEntity:
    state = db.scalar(select(State).where(State.uf == "SP"))
    muni = db.scalar(select(Municipality).where(Municipality.ibge_code == "3545209"))
    if muni is None:
        muni = Municipality(
            ibge_code="3545209", name="Salto", state_id=state.id, search_text="salto"
        )
        db.add(muni)
        db.flush()
    entity = GovernmentEntity(
        uasg="158364",
        name="IFSP - CAMPUS SALTO",
        sphere="federal",
        power="executive",
        state_id=state.id,
        municipality_id=muni.id,
        search_text=norm.build_search_text("IFSP - CAMPUS SALTO"),
    )
    db.add(entity)
    db.commit()
    return entity


def test_missing_credential_is_explicit_and_imports_nothing(db):
    run = IngestionService(db).ingest_transparencia_servidores(ORG, MES)
    assert run.status.value == "failed"
    assert run.error_count >= 1
    assert "TRANSPARENCIA_API_KEY" in (run.error_log[0] if run.error_log else "")
    assert db.scalar(select(PublicPerson)) is None


@respx.mock
def test_import_maps_remuneration_and_verifies_campus(db, monkeypatch):
    monkeypatch.setattr(settings, "transparencia_api_key", "test-key")
    _seed_campus(db)

    respx.get(url__regex=rf"{PT_SERVIDORES}\?.*orgaoServidorLotacao={ORG}.*").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "pessoa": {"nome": "MARIA DA SILVA", "cpfDescaracterizado": "***.123.456-**"},
                    "funcao": {"descricaoFuncaoCargo": "PROFESSOR EBTT"},
                },
                {
                    "id": 2,
                    "pessoa": {"nome": "JOAO DE OUTRO CAMPUS"},
                    "funcao": {"descricaoFuncaoCargo": "AUXILIAR"},
                },
            ],
        )
    )
    respx.get(url__regex=rf"{PT_SERVIDORES}/1$").mock(
        return_value=httpx.Response(
            200,
            json={"fichasCargoEfetivo": [{"uorgLotacao": {"nome": "IFSP - CAMPUS SALTO"}}]},
        )
    )
    respx.get(url__regex=rf"{PT_SERVIDORES}/2$").mock(
        return_value=httpx.Response(
            200,
            json={"fichasCargoEfetivo": [{"uorgLotacao": {"nome": "IFSP - CAMPUS CAMPINAS"}}]},
        )
    )
    respx.get(url__regex=rf"{PT_SERVIDORES}/remuneracao\?.*").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "mesAno": 202501,
                    "remuneracaoBasicaBruta": "9.114,75",
                    "valorTotalRemuneracaoAposDeducoes": "6.791,02",
                }
            ],
        )
    )

    run = IngestionService(db).ingest_transparencia_servidores(
        ORG, MES, campus_uorg="IFSP - CAMPUS SALTO"
    )

    assert run.status.value == "success"
    # Apenas a servidora do campus de Salto é associada.
    persons = list(db.scalars(select(PublicPerson)))
    assert [p.name for p in persons] == ["MARIA DA SILVA"]
    campus = db.scalar(select(GovernmentEntity).where(GovernmentEntity.uasg == "158364"))
    assert persons[0].entity_id == campus.id
    assert persons[0].masked_document == "***.123.456-**"
    assert persons[0].role_title == "PROFESSOR EBTT"

    rem = db.scalar(select(Remuneration))
    assert rem is not None
    assert float(rem.gross_amount) == 9114.75
    assert float(rem.net_amount) == 6791.02
    assert rem.reference_year == 2025 and rem.reference_month == 1


@respx.mock
def test_api_search_and_sources_without_credential(db, client, monkeypatch):
    monkeypatch.setattr(settings, "transparencia_api_key", "test-key")
    # usa o mesmo fluxo acima de forma simplificada
    _seed_campus(db)
    respx.get(url__regex=rf"{PT_SERVIDORES}\?.*").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 7, "pessoa": {"nome": "ANA SOUZA"}, "funcao": {"descricaoFuncaoCargo": "TECNICO"}}],
        )
    )
    respx.get(url__regex=rf"{PT_SERVIDORES}/7$").mock(
        return_value=httpx.Response(
            200, json={"fichasCargoEfetivo": [{"uorgLotacao": {"nome": "IFSP - CAMPUS SALTO"}}]}
        )
    )
    respx.get(url__regex=rf"{PT_SERVIDORES}/remuneracao\?.*").mock(
        return_value=httpx.Response(
            200,
            json=[{"mesAno": 202501, "remuneracaoBasicaBruta": "5.000,00", "valorTotalRemuneracaoAposDeducoes": "4.000,00"}],
        )
    )
    IngestionService(db).ingest_transparencia_servidores(ORG, MES, campus_uorg="IFSP - CAMPUS SALTO")

    listing = client.get("/api/v1/servidores", params={"uasg": "158364"})
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "ANA SOUZA"
    assert float(body["items"][0]["latest_gross"]) == 5000.0

    # Sem chave configurada de verdade, a fonte é marcada como indisponível.
    monkeypatch.setattr(settings, "transparencia_api_key", "")
    sources = client.get("/api/v1/salarios/fontes")
    assert sources.status_code == 200
    codes = {s["code"]: s for s in sources.json()}
    assert codes["transparencia"]["credentials_present"] is False
    assert codes["ifsp_dados_abertos"]["status"] == "bloqueado_waf"
