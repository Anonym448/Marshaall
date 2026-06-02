"""
Tests mínimos del API — ejecutar con: pytest tests/ -v
Requiere: las variables de entorno DB_HOST, DB_NAME, etc. apuntando a una BD válida.
Para tests rápidos sin BD real, usa el test client de Flask (mockea db()).
"""

import os
import sys
import json
import pytest

# Para importar app desde el directorio padre
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Health (público, no requiere auth)
# ---------------------------------------------------------------------------
def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["api"] == "ok"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def test_login_missing_fields(client):
    res = client.post("/api/login", json={})
    assert res.status_code == 400


def test_login_bad_credentials(client):
    res = client.post("/api/login", json={"username": "noexiste", "password": "nada"})
    assert res.status_code == 401


def test_login_success(client):
    """Depende de que exista el admin seed."""
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASS", "admin1234")
    res = client.post("/api/login", json={"username": admin_user, "password": admin_pass})
    assert res.status_code == 200
    data = res.get_json()
    assert "token" in data
    assert data["role"] == "admin"


# ---------------------------------------------------------------------------
# Auth requerida
# ---------------------------------------------------------------------------
def test_events_no_auth(client):
    res = client.get("/api/events")
    assert res.status_code == 401


def test_alerts_no_auth(client):
    res = client.get("/api/alerts")
    assert res.status_code == 401


def test_users_no_auth(client):
    res = client.get("/api/users")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Endpoints autenticados
# ---------------------------------------------------------------------------
def get_token(client):
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASS", "admin1234")
    res = client.post("/api/login", json={"username": admin_user, "password": admin_pass})
    return res.get_json()["token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_me(client):
    token = get_token(client)
    res = client.get("/api/me", headers=auth_header(token))
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "admin"


def test_events_authed(client):
    token = get_token(client)
    res = client.get("/api/events?page=1&per_page=5", headers=auth_header(token))
    assert res.status_code == 200
    data = res.get_json()
    assert "data" in data
    assert "total" in data


def test_alerts_authed(client):
    token = get_token(client)
    res = client.get("/api/alerts?page=1&per_page=5", headers=auth_header(token))
    assert res.status_code == 200
    data = res.get_json()
    assert "data" in data


def test_incidents_authed(client):
    token = get_token(client)
    res = client.get("/api/incidents?page=1&per_page=5", headers=auth_header(token))
    assert res.status_code == 200
    data = res.get_json()
    assert "data" in data


def test_stats_summary(client):
    token = get_token(client)
    res = client.get("/api/stats/summary", headers=auth_header(token))
    assert res.status_code == 200
    data = res.get_json()
    assert "total_events" in data


def test_stats_epm(client):
    token = get_token(client)
    res = client.get("/api/stats/events_per_minute?minutes=60", headers=auth_header(token))
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_users_list(client):
    token = get_token(client)
    res = client.get("/api/users", headers=auth_header(token))
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_health_detailed(client):
    res = client.get("/api/health")
    data = res.get_json()
    assert "db" in data
    assert "ingest" in data


def test_create_incident_and_detail(client):
    token = get_token(client)
    # Crear
    res = client.post("/api/incidents", headers=auth_header(token),
                      json={"title": "Test inc", "severity": 2})
    assert res.status_code == 201
    inc_id = res.get_json()["id"]

    # Detalle
    res = client.get(f"/api/incidents/{inc_id}", headers=auth_header(token))
    assert res.status_code == 200
    data = res.get_json()
    assert data["incident"]["title"] == "Test inc"

    # Actualizar estado
    res = client.patch(f"/api/incidents/{inc_id}", headers=auth_header(token),
                       json={"status": "cerrado"})
    assert res.status_code == 200


def test_correlation(client):
    token = get_token(client)
    res = client.get("/api/correlation/suggestions?minutes=5&threshold=100",
                     headers=auth_header(token))
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)
