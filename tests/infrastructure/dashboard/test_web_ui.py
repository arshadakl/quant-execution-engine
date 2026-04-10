"""Tests for Web UI (FastAPI + HTMX dashboard)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from infrastructure.dashboard.web_ui import create_app
    app = create_app(api_token="test-token")
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def auth_headers():
    return {"X-API-Token": "test-token"}


# ─── Auth ───

def test_root_requires_auth(client):
    resp = client.get("/")
    assert resp.status_code == 401


def test_root_with_valid_token(client, auth_headers):
    resp = client.get("/", headers=auth_headers)
    assert resp.status_code == 200


def test_invalid_token_rejected(client):
    resp = client.get("/", headers={"X-API-Token": "wrong"})
    assert resp.status_code == 401


# ─── Dashboard HTML ───

def test_root_returns_html(client, auth_headers):
    resp = client.get("/", headers=auth_headers)
    assert "text/html" in resp.headers["content-type"]


def test_dashboard_contains_app_name(client, auth_headers):
    resp = client.get("/", headers=auth_headers)
    assert b"ALGO" in resp.content or b"algo" in resp.content.lower()


# ─── Positions partial ───

def test_positions_endpoint_returns_html(client, auth_headers):
    resp = client.get("/partials/positions", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_positions_empty_state(client, auth_headers):
    resp = client.get("/partials/positions", headers=auth_headers)
    assert resp.status_code == 200


# ─── Signals partial ───

def test_signals_endpoint_returns_html(client, auth_headers):
    resp = client.get("/partials/signals", headers=auth_headers)
    assert resp.status_code == 200


# ─── Trade history partial ───

def test_history_endpoint_returns_html(client, auth_headers):
    resp = client.get("/partials/history", headers=auth_headers)
    assert resp.status_code == 200


# ─── Strategy toggles ───

def test_strategy_toggle_returns_html(client, auth_headers):
    resp = client.post("/strategy/orb/toggle", headers=auth_headers)
    assert resp.status_code == 200


def test_strategy_toggle_requires_auth(client):
    resp = client.post("/strategy/orb/toggle")
    assert resp.status_code == 401


def test_strategy_toggle_returns_updated_state(client, auth_headers):
    resp = client.post("/strategy/orb/toggle", headers=auth_headers)
    assert b"orb" in resp.content.lower() or b"ORB" in resp.content


# ─── Risk params ───

def test_risk_get_returns_form(client, auth_headers):
    resp = client.get("/risk", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_risk_post_updates_params(client, auth_headers):
    resp = client.post(
        "/risk",
        data={"max_daily_loss_pct": "0.02", "max_open_positions": "3"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_risk_post_requires_auth(client):
    resp = client.post("/risk", data={"max_daily_loss_pct": "0.02", "max_open_positions": "5"})
    assert resp.status_code == 401


# ─── Summary partial ───

def test_summary_endpoint_returns_html(client, auth_headers):
    resp = client.get("/partials/summary", headers=auth_headers)
    assert resp.status_code == 200
