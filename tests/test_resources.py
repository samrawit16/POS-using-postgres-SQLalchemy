"""Catalogue resources: CRUD, validation, referential integrity."""
from decimal import Decimal

import pytest


def product_body(**overrides):
    body = {"name": "Paracetamol 500mg", "sku": "SKU-001", "price": "12.50", "cost": "8.00"}
    body.update(overrides)
    return body


# ---------------------------------------------------------------- categories
def test_category_crud(client, manager):
    h = manager.headers
    parent = client.post("/categories/", json={"name": "Medicine"}, headers=h)
    assert parent.status_code == 201
    pid = parent.json()["id"]
    child = client.post("/categories/", json={"name": "Pain relief", "parent_category_id": pid}, headers=h)
    assert child.status_code == 201 and child.json()["parent_category_id"] == pid

    assert client.get(f"/categories/{pid}", headers=h).json()["name"] == "Medicine"
    assert len(client.get("/categories/", headers=h).json()) == 2

    upd = client.put(f"/categories/{pid}", json={"description": "All medicine"}, headers=h)
    assert upd.status_code == 200 and upd.json()["description"] == "All medicine"
    assert client.put(f"/categories/{pid}", json={"description": None}, headers=h).json()["description"] is None

    # Deleting a parent detaches its children (parent_category_id -> NULL); they are not deleted.
    assert client.delete(f"/categories/{pid}", headers=h).status_code == 204
    assert client.get(f"/categories/{pid}", headers=h).status_code == 404
    survivor = client.get(f"/categories/{child.json()['id']}", headers=h)
    assert survivor.status_code == 200 and survivor.json()["parent_category_id"] is None
    assert client.delete(f"/categories/{child.json()['id']}", headers=h).status_code == 204


def test_category_validation(client, manager):
    h = manager.headers
    assert client.post("/categories/", json={}, headers=h).status_code == 422
    assert client.post("/categories/", json={"name": ""}, headers=h).status_code == 422
    assert client.post("/categories/", json={"name": "   "}, headers=h).status_code == 422
    assert client.post("/categories/", json={"name": "x" * 101}, headers=h).status_code == 422
    assert client.post("/categories/", json={"name": "ok", "parent_category_id": 0}, headers=h).status_code == 422
    assert client.post("/categories/", json={"name": "ok", "description": "d" * 10_001}, headers=h).status_code == 422
    assert client.post("/categories/", json={"name": "ok", "parent_category_id": 999}, headers=h).status_code == 404
    cid = client.post("/categories/", json={"name": "A"}, headers=h).json()["id"]
    assert client.put(f"/categories/{cid}", json={"name": None}, headers=h).status_code == 422


def test_category_names_are_stored_literally(client, manager):
    """Quotes/markup/unicode are just data - parameterised queries, no interpretation."""
    for name in ["Robert'); DROP TABLE categories;--", "<script>alert(1)</script>", "Ünïcödé 日本語 💊"]:
        r = client.post("/categories/", json={"name": name}, headers=manager.headers)
        assert r.status_code == 201 and r.json()["name"] == name
    assert len(client.get("/categories/", headers=manager.headers).json()) == 3


# ---------------------------------------------------------------- suppliers
def test_supplier_crud_and_email_normalised(client, manager):
    h = manager.headers
    r = client.post("/suppliers/", json={"name": "Acme", "email": "Sales@ACME.com", "tax_id": "T-1"}, headers=h)
    assert r.status_code == 201 and r.json()["email"] == "sales@acme.com"
    sid = r.json()["id"]
    assert client.put(f"/suppliers/{sid}", json={"phone": "+251900000000"}, headers=h).json()["phone"] == "+251900000000"
    assert client.put(f"/suppliers/{sid}", json={"email": "nope"}, headers=h).status_code == 422
    assert client.post("/suppliers/", json={"name": "B", "email": "bad"}, headers=h).status_code == 422
    assert client.delete(f"/suppliers/{sid}", headers=h).status_code == 204


# ---------------------------------------------------------------- products
def test_product_crud(client, manager, cashier):
    h = manager.headers
    r = client.post("/products/", json=product_body(), headers=h)
    assert r.status_code == 201, r.text
    p = r.json()
    assert Decimal(p["price"]) == Decimal("12.50") and Decimal(p["cost"]) == Decimal("8.00") and p["is_active"] is True

    # cashiers may read...
    assert client.get(f"/products/{p['id']}", headers=cashier.headers).status_code == 200
    assert client.get("/products/", headers=cashier.headers).status_code == 200
    # ...but not change
    assert client.put(f"/products/{p['id']}", json={"price": "1.00"}, headers=cashier.headers).status_code == 403

    upd = client.put(f"/products/{p['id']}", json={"price": "15.00", "is_active": False}, headers=h)
    assert upd.status_code == 200 and Decimal(upd.json()["price"]) == Decimal("15.00") and upd.json()["is_active"] is False
    assert client.delete(f"/products/{p['id']}", headers=h).status_code == 204


def test_product_links_are_checked(client, manager):
    h = manager.headers
    cat = client.post("/categories/", json={"name": "C"}, headers=h).json()["id"]
    sup = client.post("/suppliers/", json={"name": "S"}, headers=h).json()["id"]
    ok = client.post("/products/", json=product_body(category_id=cat, supplier_id=sup), headers=h)
    assert ok.status_code == 201 and ok.json()["category_id"] == cat and ok.json()["supplier_id"] == sup

    assert client.post("/products/", json=product_body(sku="B", category_id=999), headers=h).status_code == 404
    assert client.post("/products/", json=product_body(sku="C", supplier_id=999), headers=h).status_code == 404
    pid = ok.json()["id"]
    assert client.put(f"/products/{pid}", json={"category_id": 999}, headers=h).status_code == 404
    # Deleting a category/supplier that products point at detaches them (FK -> NULL); products survive.
    assert client.delete(f"/categories/{cat}", headers=h).status_code == 204
    assert client.delete(f"/suppliers/{sup}", headers=h).status_code == 204
    after = client.get(f"/products/{pid}", headers=h).json()
    assert after["category_id"] is None and after["supplier_id"] is None


def test_duplicate_sku_is_409_and_leaks_nothing(client, manager):
    h = manager.headers
    assert client.post("/products/", json=product_body(), headers=h).status_code == 201
    r = client.post("/products/", json=product_body(name="Other"), headers=h)
    assert r.status_code == 409
    text = r.text.lower()
    for leak in ("unique", "violates", "sqlalchemy", "psycopg", "insert into", "constraint"):
        assert leak not in text
    # the failed insert must not poison later requests
    assert client.post("/products/", json=product_body(sku="SKU-002"), headers=h).status_code == 201


def test_updating_sku_to_existing_one_is_409(client, manager):
    h = manager.headers
    client.post("/products/", json=product_body(sku="A"), headers=h)
    b = client.post("/products/", json=product_body(sku="B"), headers=h).json()["id"]
    assert client.put(f"/products/{b}", json={"sku": "A"}, headers=h).status_code == 409


@pytest.mark.parametrize("override", [
    {"price": "-1.00"}, {"price": "1.234"}, {"price": "12345678901.00"}, {"price": "abc"}, {"price": None},
    {"cost": "-0.01"}, {"name": ""}, {"name": "x" * 256}, {"sku": ""}, {"sku": "s" * 101},
    {"expiry_date": "not-a-date"}, {"category_id": -5}, {"is_active": "maybe"},
])
def test_product_validation(client, manager, override):
    assert client.post("/products/", json=product_body(**override), headers=manager.headers).status_code == 422


def test_product_required_fields(client, manager):
    for missing in ("name", "sku", "price"):
        body = product_body()
        body.pop(missing)
        assert client.post("/products/", json=body, headers=manager.headers).status_code == 422


def test_product_update_null_rules(client, manager):
    pid = client.post("/products/", json=product_body(barcode="123"), headers=manager.headers).json()["id"]
    assert client.put(f"/products/{pid}", json={"barcode": None}, headers=manager.headers).json()["barcode"] is None
    for field in ("name", "sku", "price", "cost", "is_active"):
        assert client.put(f"/products/{pid}", json={field: None}, headers=manager.headers).status_code == 422, field


def test_empty_update_is_a_noop(client, manager):
    pid = client.post("/products/", json=product_body(), headers=manager.headers).json()["id"]
    r = client.put(f"/products/{pid}", json={}, headers=manager.headers)
    assert r.status_code == 200 and r.json()["sku"] == "SKU-001"


def test_mass_assignment_of_unknown_fields_is_ignored(client, manager):
    r = client.post("/products/", json=product_body(id=9999, created_at="2000-01-01", evil="x"), headers=manager.headers)
    assert r.status_code == 201 and r.json()["id"] != 9999 and "evil" not in r.json()


# ---------------------------------------------------------------- inventory
def test_inventory_crud_and_rules(client, manager, cashier):
    h = manager.headers
    pid = client.post("/products/", json=product_body(), headers=h).json()["id"]
    r = client.post("/inventory/", json={"product_id": pid, "quantity": 50, "batch_number": "B1"}, headers=h)
    assert r.status_code == 201 and r.json()["quantity"] == 50 and r.json()["reorder_level"] == 10
    iid = r.json()["id"]

    assert client.post("/inventory/", json={"product_id": pid, "quantity": 1}, headers=h).status_code == 400  # one row per product
    assert client.post("/inventory/", json={"product_id": 999, "quantity": 1}, headers=h).status_code == 404
    assert client.get(f"/inventory/{iid}", headers=cashier.headers).status_code == 200  # cashiers can check stock

    assert client.put(f"/inventory/{iid}", json={"quantity": 45}, headers=h).json()["quantity"] == 45
    assert client.put(f"/inventory/{iid}", json={"product_id": 999}, headers=h).status_code == 404
    assert client.put(f"/inventory/{iid}", json={"quantity": 1}, headers=cashier.headers).status_code == 403
    # a product with stock rows can't be deleted out from under them
    assert client.delete(f"/products/{pid}", headers=h).status_code == 409
    assert client.delete(f"/inventory/{iid}", headers=h).status_code == 204


@pytest.mark.parametrize("override", [{"quantity": -1}, {"reorder_level": -1}, {"quantity": 2**31},
                                      {"quantity": 1.5}, {"quantity": "many"}, {"batch_number": "b" * 101}])
def test_inventory_validation(client, manager, override):
    pid = client.post("/products/", json=product_body(), headers=manager.headers).json()["id"]
    assert client.post("/inventory/", json={"product_id": pid, **override}, headers=manager.headers).status_code == 422


def test_huge_ids_and_quantities_are_422_not_500(client, manager):
    """Values above int4 would make PostgreSQL raise 'integer out of range'."""
    assert client.post("/inventory/", json={"product_id": 2**40, "quantity": 1}, headers=manager.headers).status_code == 422
    assert client.get(f"/products/{2**40}", headers=manager.headers).status_code == 422
