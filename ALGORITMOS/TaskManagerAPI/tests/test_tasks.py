# tests/test_tasks.py
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_and_get(client):
    r = client.post("/tasks/", json={"title": "Comprar leche", "description": "2L"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Comprar leche"
    assert data["done"] is False
    task_id = data["id"]

    r = client.get(f"/tasks/{task_id}")
    assert r.status_code == 200
    assert r.json()["id"] == task_id


def test_list_tasks(client):
    client.post("/tasks/", json={"title": "A"})
    client.post("/tasks/", json={"title": "B"})
    r = client.get("/tasks/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_update_task(client):
    r = client.post("/tasks/", json={"title": "Original"})
    task_id = r.json()["id"]
    r = client.patch(f"/tasks/{task_id}", json={"title": "Actualizado", "done": True})
    assert r.status_code == 200
    assert r.json()["title"] == "Actualizado"
    assert r.json()["done"] is True


def test_delete_task(client):
    r = client.post("/tasks/", json={"title": "Borrar"})
    task_id = r.json()["id"]
    r = client.delete(f"/tasks/{task_id}")
    assert r.status_code == 204
    r = client.get(f"/tasks/{task_id}")
    assert r.status_code == 404


def test_not_found(client):
    r = client.get("/tasks/9999")
    assert r.status_code == 404