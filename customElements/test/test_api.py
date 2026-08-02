from fastapi.testclient import TestClient


def test_api_root(api_client: TestClient) -> None:
    r = api_client.get("/")
    assert r.status_code == 200


def test_api_search(api_client: TestClient) -> None:
    r = api_client.post("/search?screenCd=car_list", json={"params": {}})
    assert r.status_code == 200
    assert r.json() == []


def test_api_search_with_params(api_client: TestClient) -> None:
    api_client.post("/register?screenCd=car_list", json={
        "insertList": [{"make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1}],
        "deleteList": [],
        "updateList": [],
    })
    r = api_client.post("/search?screenCd=car_list", json={"params": {"make": "Tesla"}})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["model"] == "Model 3"


def test_api_search_invalid_key_returns_418(api_client: TestClient) -> None:
    r = api_client.post("/search?screenCd=car_list", json={"params": {"bogus_key": 1}})
    assert r.status_code == 418
    assert r.json() == {"message": "invalid key: bogus_key"}


def test_api_register_insert(api_client: TestClient) -> None:
    r = api_client.post("/register?screenCd=car_list", json={
        "insertList": [{"make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1}],
        "deleteList": [],
        "updateList": [],
    })
    assert r.status_code == 200
    r = api_client.post("/search?screenCd=car_list", json={"params": {}})
    assert len(r.json()) == 1


def test_api_getClass(api_client: TestClient) -> None:
    r = api_client.get("/getClass", params={"code": "make"})
    assert r.status_code == 200
    assert r.json() == [
        {"value": "cdFord", "name": "Ford"},
        {"value": "cdTesla", "name": "Tesla"},
        {"value": "cdToyota", "name": "Toyota"},
    ]


def test_api_getColumns(api_client: TestClient) -> None:
    r = api_client.get("/getColumns", params={"screenCd": "car_list"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"columnOptions", "rowStyles"}
    make = next(c for c in body["columnOptions"] if c["column_cd"] == "make")
    assert make["type"] == "dropdown"
    assert make["classes"] == [
        {"value": "cdFord", "name": "Ford"},
        {"value": "cdTesla", "name": "Tesla"},
        {"value": "cdToyota", "name": "Toyota"},
    ]


def test_api_getSearchForms(api_client: TestClient) -> None:
    r = api_client.get("/getSearchForms", params={"screenCd": "car_list"})
    assert r.status_code == 200
    assert [f["search_form_cd"] for f in r.json()] == ["make", "model", "price", "electric"]


# -------------------------------------------------------------
# SQLインジェクション対策のテスト（API層）
# -------------------------------------------------------------
def test_api_search_injection_safe(api_client: TestClient) -> None:
    api_client.post("/register?screenCd=car_list", json={
        "insertList": [{"make": "Tesla", "model": "Model 3", "price": 50000, "electric": 1}],
        "deleteList": [],
        "updateList": [],
    })
    for payload in ["' OR '1'='1", "' UNION SELECT 1,2,3,4--", "'; DROP TABLE car;--"]:
        r = api_client.post("/search?screenCd=car_list", json={"params": {"model": payload}})
        assert r.status_code == 200
        assert r.json() == []


def test_api_register_injection_value_safe(api_client: TestClient) -> None:
    payload = "'); DROP TABLE car; --"
    r = api_client.post("/register?screenCd=car_list", json={
        "insertList": [{"make": "Tesla", "model": payload, "price": 50000, "electric": 1}],
        "deleteList": [],
        "updateList": [],
    })
    assert r.status_code == 200
    r = api_client.post("/search?screenCd=car_list", json={"params": {"model": payload}})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["model"] == payload


def test_api_search_injection_key_418(api_client: TestClient) -> None:
    for key in ["`model`", "model' OR '1'='1", "' OR 1=1--"]:
        r = api_client.post("/search?screenCd=car_list", json={"params": {key: 1}})
        assert r.status_code == 418
        assert r.json() == {"message": f"invalid key: {key}"}


def test_api_register_injection_key_418(api_client: TestClient) -> None:
    r = api_client.post("/register?screenCd=car_list", json={
        "insertList": [{"make`=1, model='x' --": 1}],
        "deleteList": [],
        "updateList": [],
    })
    assert r.status_code == 418


# -------------------------------------------------------------
# CSRFトークン検証
# -------------------------------------------------------------
def test_api_get_csrf_token_sets_cookie(api_client: TestClient) -> None:
    r = api_client.get("/getCsrfToken")
    assert r.status_code == 200
    assert r.json() == {"type": "ok"}
    assert api_client.cookies.get("csrftoken")


def test_api_csrf_missing_token_rejected(api_client_no_csrf: TestClient) -> None:
    r = api_client_no_csrf.post("/search?screenCd=car_list", json={"params": {}})
    assert r.status_code == 403


def test_api_csrf_wrong_token_rejected(api_client_no_csrf: TestClient) -> None:
    api_client_no_csrf.get("/getCsrfToken")
    r = api_client_no_csrf.post(
        "/search?screenCd=car_list",
        json={"params": {}},
        headers={"csrftoken": "wrong-token"},
    )
    assert r.status_code == 403


def test_api_injection_no_table_damage(api_client: TestClient) -> None:
    payloads = ["' OR '1'='1", "' UNION SELECT 1,2,3,4--", "'; DROP TABLE car;--"]
    for payload in payloads:
        api_client.post("/search?screenCd=car_list", json={"params": {"model": payload}})
        api_client.post("/register?screenCd=car_list", json={
            "insertList": [{"make": "Tesla", "model": payload, "price": 1, "electric": 0}],
            "deleteList": [payload],
            "updateList": [{"id": payload, "price": 1}],
        })
    r = api_client.post("/search?screenCd=car_list", json={"params": {}})
    assert r.status_code == 200
    r = api_client.get("/getColumns", params={"screenCd": "car_list"})
    assert r.status_code == 200
