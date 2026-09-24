"""Customer records contain personal + health data: cashiers must not see or set the health fields."""
import pytest

CUSTOMER = {"first_name": "Sam", "last_name": "Rit", "email": "Sam@Example.com", "phone": "0911",
            "medical_conditions": "asthma", "insurance_provider": "Acme Health"}


@pytest.fixture()
def customer_id(client, manager):
    r = client.post("/customers/", json=CUSTOMER, headers=manager.headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_manager_sees_medical_conditions(client, manager, customer_id):
    r = client.get(f"/customers/{customer_id}", headers=manager.headers)
    assert r.json()["medical_conditions"] == "asthma" and r.json()["email"] == "sam@example.com"
    assert client.get("/customers/", headers=manager.headers).json()[0]["medical_conditions"] == "asthma"


def test_cashier_sees_customer_but_not_medical_conditions(client, cashier, customer_id):
    one = client.get(f"/customers/{customer_id}", headers=cashier.headers).json()
    many = client.get("/customers/", headers=cashier.headers).json()[0]
    for c in (one, many):
        assert c["first_name"] == "Sam" and c["insurance_provider"] == "Acme Health"
        assert c["medical_conditions"] is None
    assert "asthma" not in client.get("/customers/", headers=cashier.headers).text


def test_cashier_cannot_set_medical_conditions(client, cashier, customer_id):
    assert client.post("/customers/", json=CUSTOMER, headers=cashier.headers).status_code == 403
    basic = {k: v for k, v in CUSTOMER.items() if k != "medical_conditions"}
    ok = client.post("/customers/", json={**basic, "email": "new@example.com"}, headers=cashier.headers)
    assert ok.status_code == 201 and ok.json()["medical_conditions"] is None

    assert client.put(f"/customers/{customer_id}", json={"medical_conditions": "overwritten"}, headers=cashier.headers).status_code == 403
    assert client.put(f"/customers/{customer_id}", json={"medical_conditions": None}, headers=cashier.headers).status_code == 403


def test_cashier_update_response_does_not_leak_and_does_not_erase(client, cashier, manager, customer_id):
    r = client.put(f"/customers/{customer_id}", json={"phone": "0922"}, headers=cashier.headers)
    assert r.status_code == 200 and r.json()["phone"] == "0922" and r.json()["medical_conditions"] is None
    # the stored value is untouched by the cashier's edit
    assert client.get(f"/customers/{customer_id}", headers=manager.headers).json()["medical_conditions"] == "asthma"


def test_cashier_cannot_delete_customers(client, cashier, manager, customer_id):
    assert client.delete(f"/customers/{customer_id}", headers=cashier.headers).status_code == 403
    assert client.delete(f"/customers/{customer_id}", headers=manager.headers).status_code == 204


def test_duplicate_customer_email_is_409(client, manager, customer_id):
    assert client.post("/customers/", json={**CUSTOMER, "email": "SAM@example.com"}, headers=manager.headers).status_code == 409


@pytest.mark.parametrize("override", [{"first_name": ""}, {"email": "nope"}, {"phone": "1" * 21},
                                      {"date_of_birth": "31-12-1990"}, {"medical_conditions": "m" * 10_001}])
def test_customer_validation(client, manager, override):
    assert client.post("/customers/", json={**CUSTOMER, **override}, headers=manager.headers).status_code == 422


def test_deleting_a_customer_keeps_their_sales_but_detaches_them(client, manager, cashier, customer_id):
    r = client.post("/sales/", json={"user_id": cashier.user.id, "customer_id": customer_id}, headers=cashier.headers)
    assert r.status_code == 201
    assert client.delete(f"/customers/{customer_id}", headers=manager.headers).status_code == 204
    sale = client.get(f"/sales/{r.json()['id']}", headers=manager.headers).json()
    assert sale["customer_id"] is None  # sale record survives, personal link is gone
