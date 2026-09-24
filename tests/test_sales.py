"""Sales workflow: sale -> items -> payment -> receipt, with cashier ownership rules."""
from decimal import Decimal

import pytest


@pytest.fixture()
def product(client, manager):
    r = client.post("/products/", json={"name": "Widget", "sku": "W-1", "price": "10.00"}, headers=manager.headers)
    assert r.status_code == 201
    return r.json()


def item_body(sale_id, product_id, **overrides):
    body = {"sale_id": sale_id, "product_id": product_id, "quantity": 2, "unit_price": "10.00", "total_price": "20.00"}
    body.update(overrides)
    return body


def make_sale(client, who, **overrides):
    body = {"user_id": who.user.id, "total_amount": "20.00"}
    body.update(overrides)
    return client.post("/sales/", json=body, headers=who.headers)


# ---------------------------------------------------------------- happy path
def test_full_sale_flow_as_cashier(client, cashier, product):
    h = cashier.headers
    sale = make_sale(client, cashier)
    assert sale.status_code == 201, sale.text
    sid = sale.json()["id"]
    assert sale.json()["user_id"] == cashier.user.id and sale.json()["sale_date"]

    item = client.post("/sale-items/", json=item_body(sid, product["id"]), headers=h)
    assert item.status_code == 201 and item.json()["quantity"] == 2
    pay = client.post("/payments/", json={"sale_id": sid, "payment_method": "cash", "amount": "20.00"}, headers=h)
    assert pay.status_code == 201 and pay.json()["status"] == "completed"
    rec = client.post("/receipts/", json={"sale_id": sid, "receipt_number": "R-0001", "receipt_data": "Widget x2 = 20.00"}, headers=h)
    assert rec.status_code == 201 and rec.json()["receipt_number"] == "R-0001"

    for path, key in (("/sales/", sid), ("/sale-items/", item.json()["id"]), ("/payments/", pay.json()["id"]),
                      ("/receipts/", rec.json()["id"])):
        assert client.get(f"{path}{key}", headers=h).status_code == 200
        assert len(client.get(path, headers=h).json()) == 1


def test_manager_can_create_sale_on_behalf_of_cashier(client, manager, cashier):
    assert make_sale(client, manager, user_id=cashier.user.id).status_code == 201


# ---------------------------------------------------------------- ownership
def test_cashier_cannot_create_sale_as_someone_else(client, cashier, manager):
    r = make_sale(client, cashier, user_id=manager.user.id)
    assert r.status_code == 403
    assert client.get("/sales/", headers=manager.headers).json() == []  # nothing was created


def test_cashier_cannot_touch_another_cashiers_sale(client, login_as, product):
    alice, bob = login_as("cashier"), login_as("cashier")
    sid = make_sale(client, alice).json()["id"]
    assert client.post("/sale-items/", json=item_body(sid, product["id"]), headers=bob.headers).status_code == 403
    assert client.post("/payments/", json={"sale_id": sid, "payment_method": "cash", "amount": "1.00"}, headers=bob.headers).status_code == 403
    assert client.post("/receipts/", json={"sale_id": sid, "receipt_number": "X", "receipt_data": "d"}, headers=bob.headers).status_code == 403
    # the owner still can
    assert client.post("/sale-items/", json=item_body(sid, product["id"]), headers=alice.headers).status_code == 201


def test_manager_can_add_to_any_sale(client, manager, cashier, product):
    sid = make_sale(client, cashier).json()["id"]
    assert client.post("/sale-items/", json=item_body(sid, product["id"]), headers=manager.headers).status_code == 201
    assert client.post("/payments/", json={"sale_id": sid, "payment_method": "card", "amount": "5.00"}, headers=manager.headers).status_code == 201


def test_ownership_check_cannot_be_bypassed_by_missing_sale(client, cashier, product):
    assert client.post("/sale-items/", json=item_body(9999, product["id"]), headers=cashier.headers).status_code == 404


def test_cashier_cannot_alter_or_delete_completed_transactions(client, cashier, product):
    h = cashier.headers
    sid = make_sale(client, cashier).json()["id"]
    iid = client.post("/sale-items/", json=item_body(sid, product["id"]), headers=h).json()["id"]
    pid = client.post("/payments/", json={"sale_id": sid, "payment_method": "cash", "amount": "20.00"}, headers=h).json()["id"]
    rid = client.post("/receipts/", json={"sale_id": sid, "receipt_number": "R1", "receipt_data": "d"}, headers=h).json()["id"]

    for path, key in (("/sales/", sid), ("/sale-items/", iid), ("/payments/", pid), ("/receipts/", rid)):
        assert client.put(f"{path}{key}", json={}, headers=h).status_code == 403
        assert client.delete(f"{path}{key}", headers=h).status_code == 403
    # nothing changed
    assert Decimal(client.get(f"/payments/{pid}", headers=h).json()["amount"]) == Decimal("20.00")


def test_manager_can_correct_and_delete(client, manager, cashier, product):
    sid = make_sale(client, cashier).json()["id"]
    iid = client.post("/sale-items/", json=item_body(sid, product["id"]), headers=cashier.headers).json()["id"]
    r = client.put(f"/sale-items/{iid}", json={"quantity": 3, "total_price": "30.00"}, headers=manager.headers)
    assert r.status_code == 200 and r.json()["quantity"] == 3
    assert client.put(f"/sales/{sid}", json={"discount_amount": "2.00"}, headers=manager.headers).status_code == 200
    assert client.delete(f"/sale-items/{iid}", headers=manager.headers).status_code == 204


def test_deleting_a_sale_cascades_to_its_children(client, manager, cashier, product):
    h = cashier.headers
    sid = make_sale(client, cashier).json()["id"]
    client.post("/sale-items/", json=item_body(sid, product["id"]), headers=h)
    client.post("/payments/", json={"sale_id": sid, "payment_method": "cash", "amount": "20.00"}, headers=h)
    client.post("/receipts/", json={"sale_id": sid, "receipt_number": "R1", "receipt_data": "d"}, headers=h)
    assert client.delete(f"/sales/{sid}", headers=manager.headers).status_code == 204
    for path in ("/sale-items/", "/payments/", "/receipts/"):
        assert client.get(path, headers=manager.headers).json() == []


# ---------------------------------------------------------------- validation
@pytest.mark.parametrize("override", [
    {"quantity": 0}, {"quantity": -3}, {"quantity": 1.5}, {"quantity": 2**31},
    {"unit_price": "-1.00"}, {"discount_amount": "-1.00"}, {"total_price": "-20.00"},
    {"unit_price": "1.005"}, {"total_price": "100000000000.00"},
])
def test_sale_item_validation(client, cashier, product, override):
    sid = make_sale(client, cashier).json()["id"]
    assert client.post("/sale-items/", json=item_body(sid, product["id"], **override), headers=cashier.headers).status_code == 422


@pytest.mark.parametrize("override", [
    {"amount": "0"}, {"amount": "-5.00"}, {"amount": "1.999"}, {"amount": "abc"},
    {"payment_method": ""}, {"payment_method": "x" * 21}, {"status": "y" * 21},
])
def test_payment_validation(client, cashier, override):
    sid = make_sale(client, cashier).json()["id"]
    body = {"sale_id": sid, "payment_method": "cash", "amount": "10.00", **override}
    assert client.post("/payments/", json=body, headers=cashier.headers).status_code == 422


@pytest.mark.parametrize("override", [
    {"tax_amount": "-1"}, {"discount_amount": "-1"}, {"total_amount": "-0.01"}, {"total_amount": "1.234"},
    {"total_amount": "10000000000000.00"}, {"customer_id": 0}, {"user_id": 0}, {"user_id": None},
])
def test_sale_validation(client, manager, override):
    body = {"user_id": manager.user.id, **override}
    assert client.post("/sales/", json=body, headers=manager.headers).status_code == 422


def test_sale_requires_user_id(client, cashier):
    assert client.post("/sales/", json={}, headers=cashier.headers).status_code == 422


def test_unknown_references_are_404(client, manager, cashier, product):
    assert make_sale(client, manager, user_id=99999).status_code == 404
    assert make_sale(client, cashier, customer_id=99999).status_code == 404
    sid = make_sale(client, cashier).json()["id"]
    assert client.post("/sale-items/", json=item_body(sid, 99999), headers=cashier.headers).status_code == 404
    assert client.post("/payments/", json={"sale_id": 99999, "payment_method": "cash", "amount": "1.00"}, headers=cashier.headers).status_code == 404
    assert client.post("/receipts/", json={"sale_id": 99999, "receipt_number": "Z", "receipt_data": "d"}, headers=cashier.headers).status_code == 404
    assert client.put(f"/sales/{sid}", json={"user_id": 99999}, headers=manager.headers).status_code == 404


def test_receipt_rules(client, cashier):
    h = cashier.headers
    a, b = make_sale(client, cashier).json()["id"], make_sale(client, cashier).json()["id"]
    assert client.post("/receipts/", json={"sale_id": a, "receipt_number": "R1", "receipt_data": "d"}, headers=h).status_code == 201
    dup_sale = client.post("/receipts/", json={"sale_id": a, "receipt_number": "R2", "receipt_data": "d"}, headers=h)
    assert dup_sale.status_code == 400  # one receipt per sale
    dup_number = client.post("/receipts/", json={"sale_id": b, "receipt_number": "R1", "receipt_data": "d"}, headers=h)
    assert dup_number.status_code == 409  # receipt numbers are unique
    assert client.post("/receipts/", json={"sale_id": b, "receipt_number": "", "receipt_data": "d"}, headers=h).status_code == 422
    assert client.post("/receipts/", json={"sale_id": b, "receipt_number": "R3", "receipt_data": "x" * 100_001}, headers=h).status_code == 422


def test_sale_with_items_cannot_be_orphaned_by_product_delete(client, manager, cashier, product):
    sid = make_sale(client, cashier).json()["id"]
    client.post("/sale-items/", json=item_body(sid, product["id"]), headers=cashier.headers)
    assert client.delete(f"/products/{product['id']}", headers=manager.headers).status_code == 409
