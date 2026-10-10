from tests.fixtures import create_computer_dataset


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_coverage(client, db):
    create_computer_dataset(db)
    response = client.get("/api/v1/meta/coverage")
    assert response.status_code == 200
    assert response.json()["contratacoes"] >= 6


def test_search_endpoint(client, db):
    create_computer_dataset(db)
    response = client.get("/api/v1/search", params={"q": "computadores"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 6
    assert any(g["type"] == "procurement" for g in body["groups"])


def test_search_suggest_endpoint(client, db):
    create_computer_dataset(db)
    response = client.get("/api/v1/search/suggest", params={"q": "Camp"})
    assert response.status_code == 200
    assert any(item["label"] == "Campinas" for item in response.json())


def test_procurement_detail_endpoint(client, db):
    data = create_computer_dataset(db)
    response = client.get(f"/api/v1/contratacoes/{data['outlier_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert body["results"]
    assert body["source_url"]


def test_supplier_detail_aggregates(client, db):
    data = create_computer_dataset(db)
    supplier_id = data["supplier"].id
    response = client.get(f"/api/v1/fornecedores/{supplier_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["contract_count"] >= 0
    assert body["procurement_count"] >= 1


def test_entity_and_municipality_endpoints(client, db):
    data = create_computer_dataset(db)
    entity = client.get(f"/api/v1/orgaos/{data['entity'].id}")
    assert entity.status_code == 200
    muni = client.get(f"/api/v1/municipios/{data['municipality'].ibge_code}")
    assert muni.status_code == 200
    assert muni.json()["name"] == "Campinas"


def test_sources_endpoint(client):
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    codes = {s["code"] for s in response.json()}
    assert "pncp" in codes


def test_findings_require_auth_for_review(client):
    response = client.patch("/api/v1/achados/FND-NAOEXISTE/revisao", json={"status": "em_analise"})
    assert response.status_code == 401


def test_auth_flow(client):
    register = client.post(
        "/api/v1/auth/registrar",
        json={"email": "cidadao@example.com", "full_name": "Cidadão Teste", "password": "senha12345"},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "cidadao@example.com", "password": "senha12345"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/eu", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "cidadao@example.com"
