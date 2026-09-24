"""Update/delete paths: re-pointing records at other records must be validated."""
import pytest


@pytest.fixture()
def world(client, manager, cashier):
    """Two sales (one with an item, payment and receipt) plus a product, category, supplier, customer."""
    m, c = manager.headers, cashier.headers
    product = client.post("/products/", json={"name": "W", "sku": "W-1", "price": "10.00"}, headers=m).json()["id"]
    category = client.post("/categories/", json={"name": "Cat"}, headers=m).json()["id"]
    customer = client.post("/customers/", json={"first_name": "A", "last_name": "B"}, headers=m).json()["id"]
    sale1 = client.post("/sales/", json={"user_id": cashier.user.id}, headers=c).json()["id"]
    sale2 = client.post("/sales/", json={"user_id": cashier.user.id}, headers=c).json()["id"]
    item = client.post("/sale-items/", json={"sale_id": sale1, "product_id": product, "quantity": 1,
                                             "unit_price": "10.00", "total_price": "10.00"}, headers=c).json()["id"]
    payment = client.post("/payments/", json={"sale_id": sale1, "payment_method": "cash", "amount": "10.00"}, headers=c).json()["id"]
    receipt = client.post("/receipts/", json={"sale_id": sale1, "receipt_number": "R1", "receipt_data": "d"}, headers=c).json()["id"]
    return dict(product=product, category=category, customer=customer, sale1=sale1, sale2=sale2,
                item=item, payment=payment, receipt=receipt)


def test_payment_update_and_repoint(client, manager, world):
    h, pid = manager.headers, world["payment"]
    r = client.put(f"/payments/{pid}", json={"status": "refunded", "amount": "9.50"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "refunded"
    assert client.put(f"/payments/{pid}", json={"sale_id": world["sale2"]}, headers=h).json()["sale_id"] == world["sale2"]
    assert client.put(f"/payments/{pid}", json={"sale_id": 99999}, headers=h).status_code == 404
    assert client.put("/payments/99999", json={"status": "x"}, headers=h).status_code == 404
    assert client.put(f"/payments/{pid}", json={"amount": "0"}, headers=h).status_code == 422
    assert client.delete(f"/payments/{pid}", headers=h).status_code == 204


def test_receipt_update_and_repoint(client, manager, world):
    h, rid = manager.headers, world["receipt"]
    r = client.put(f"/receipts/{rid}", json={"emailed_at": "2026-01-02T03:04:05Z"}, headers=h)
    assert r.status_code == 200 and r.json()["emailed_at"].startswith("2026-01-02")
    assert client.put(f"/receipts/{rid}", json={"emailed_at": None}, headers=h).json()["emailed_at"] is None
    assert client.put(f"/receipts/{rid}", json={"sale_id": world["sale2"]}, headers=h).json()["sale_id"] == world["sale2"]
    assert client.put(f"/receipts/{rid}", json={"sale_id": 99999}, headers=h).status_code == 404
    assert client.put(f"/receipts/{rid}", json={"receipt_number": None}, headers=h).status_code == 422
    assert client.delete(f"/receipts/{rid}", headers=h).status_code == 204


def test_sale_item_update_validates_links(client, manager, world):
    h, iid = manager.headers, world["item"]
    assert client.put(f"/sale-items/{iid}", json={"sale_id": world["sale2"]}, headers=h).json()["sale_id"] == world["sale2"]
    assert client.put(f"/sale-items/{iid}", json={"sale_id": 99999}, headers=h).status_code == 404
    assert client.put(f"/sale-items/{iid}", json={"product_id": 99999}, headers=h).status_code == 404
    assert client.put(f"/sale-items/{iid}", json={"quantity": 0}, headers=h).status_code == 422


def test_sale_update_validates_links(client, manager, world):
    h, sid = manager.headers, world["sale1"]
    assert client.put(f"/sales/{sid}", json={"customer_id": world["customer"]}, headers=h).json()["customer_id"] == world["customer"]
    assert client.put(f"/sales/{sid}", json={"customer_id": None}, headers=h).json()["customer_id"] is None
    assert client.put(f"/sales/{sid}", json={"customer_id": 99999}, headers=h).status_code == 404
    assert client.put(f"/sales/{sid}", json={"user_id": None}, headers=h).status_code == 422


def test_category_and_product_update_validate_links(client, manager, world):
    h = manager.headers
    cid = world["category"]
    assert client.put(f"/categories/{cid}", json={"parent_category_id": 99999}, headers=h).status_code == 404
    other = client.post("/categories/", json={"name": "Other"}, headers=h).json()["id"]
    assert client.put(f"/categories/{cid}", json={"parent_category_id": other}, headers=h).json()["parent_category_id"] == other
    assert client.put(f"/products/{world['product']}", json={"supplier_id": 99999}, headers=h).status_code == 404
    sup = client.post("/suppliers/", json={"name": "S"}, headers=h).json()["id"]
    assert client.put(f"/products/{world['product']}", json={"supplier_id": sup}, headers=h).json()["supplier_id"] == sup
