"""Admin API tokens: CRUD, scopes, legacy key."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.deps import get_current_user, hash_password
from config import settings
from database import get_db
from main import app
from models.api_token import ApiToken
from models.user import User
from services import import_service, trading_service
from services.api_tokens import hash_api_token
from tests.conftest import scalars_by_model


@pytest.fixture
def superadmin_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="superadmin",
        password_hash=hash_password("secret"),
        role="superadmin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="subadmin",
        password_hash=hash_password("secret"),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def superadmin_client(mock_db, superadmin_user):
    def override_db():
        yield mock_db

    def override_user():
        return superadmin_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(mock_db, admin_user):
    def override_db():
        yield mock_db

    def override_user():
        return admin_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_token_row(*, plain: str, scopes: list[str], revoked: bool = False) -> ApiToken:
    now = datetime.now(timezone.utc)
    return ApiToken(
        id=uuid.uuid4(),
        name="Bot",
        token_prefix=plain[:12],
        token_hash=hash_api_token(plain),
        scopes=scopes,
        created_by_id=uuid.uuid4(),
        created_at=now,
        last_used_at=None,
        expires_at=None,
        revoked_at=now if revoked else None,
    )


def test_admin_api_tokens_forbidden_for_regular_admin(admin_client):
    assert admin_client.get("/api/admin/api-tokens").status_code == 403


def test_create_list_and_revoke_api_token(superadmin_client, mock_db):
    stored: list[ApiToken] = []

    def add(obj):
        if isinstance(obj, ApiToken):
            stored.append(obj)
        return None

    mock_db.add.side_effect = add
    mock_db.commit.side_effect = lambda: None
    mock_db.refresh.side_effect = lambda obj: None
    mock_db.get.side_effect = lambda _model, pk: next((t for t in stored if t.id == pk), None)
    mock_db.scalars.side_effect = scalars_by_model({"ApiToken": stored})

    create = superadmin_client.post(
        "/api/admin/api-tokens",
        json={"name": "Import bot", "scopes": ["import", "market_scan"]},
    )
    assert create.status_code == 200
    body = create.json()
    assert body["token"].startswith("lu4_")
    assert body["item"]["name"] == "Import bot"
    assert set(body["item"]["scopes"]) == {"import", "market_scan"}
    assert len(stored) == 1

    listed = superadmin_client.get("/api/admin/api-tokens")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert "token" not in items[0]

    token_id = items[0]["id"]
    revoked = superadmin_client.delete(f"/api/admin/api-tokens/{token_id}")
    assert revoked.status_code == 200
    assert revoked.json()["is_active"] is False


def test_import_scope_enforcement(superadmin_client, mock_db, monkeypatch):
    plain = "lu4_testtoken1234567890abcd"
    row = _make_token_row(plain=plain, scopes=["import"])
    mock_db.scalar.return_value = row
    mock_db.commit.side_effect = lambda: None

    import_id = uuid.uuid4()

    def fake_import(_db, _body):
        return SimpleNamespace(
            import_id=import_id,
            records_count=1,
            matched_count=1,
            unmatched_count=0,
        )

    monkeypatch.setattr(import_service, "import_price_records", fake_import)

    ok = superadmin_client.post(
        "/api/import",
        headers={"X-Api-Key": plain},
        json={
            "source": "test",
            "records": [
                {
                    "product_name": "Sword",
                    "seller": "Shop",
                    "price": "100",
                }
            ],
        },
    )
    assert ok.status_code == 200

    denied = superadmin_client.post(
        "/api/trading/inventory-scan",
        headers={"X-Api-Key": plain},
        json={"name": "Hero", "adena": 10, "master_coin": 0, "items": []},
    )
    assert denied.status_code == 403


def test_legacy_import_api_key_has_all_scopes(client, mock_db, monkeypatch):
    snap_id = uuid.uuid4()
    char_out = SimpleNamespace(
        id=uuid.uuid4(),
        kind="player",
        nick="Hero",
        clean_adena=10,
        master_coin=0,
        description=None,
        sort_order=0,
        updated_at=datetime.now(timezone.utc),
    )

    def fake_upsert(_db, _body):
        return SimpleNamespace(
            character=char_out,
            snapshot_id=snap_id,
            created=True,
            matched_count=0,
            unmatched_count=0,
        )

    monkeypatch.setattr(trading_service, "upsert_inventory_scan", fake_upsert)
    mock_db.scalar.return_value = None

    r = client.post(
        "/api/trading/inventory-scan",
        json={"name": "Hero", "adena": 10, "master_coin": 0, "items": []},
        headers={"X-Api-Key": settings.import_api_key},
    )
    assert r.status_code == 200


def test_revoked_token_returns_401(superadmin_client, mock_db):
    plain = "lu4_revokedtoken1234567890ab"
    row = _make_token_row(plain=plain, scopes=["import"], revoked=True)
    mock_db.scalar.return_value = row

    r = superadmin_client.post(
        "/api/import",
        headers={"X-Api-Key": plain},
        json={
            "source": "test",
            "records": [{"product_name": "Sword", "seller": "Shop", "price": "100"}],
        },
    )
    assert r.status_code == 401


def test_raid_life_scope_is_valid():
    from schemas.api_token import API_TOKEN_SCOPES, SCOPE_LABELS

    assert "raid_life" in API_TOKEN_SCOPES
    assert "raid_life" in SCOPE_LABELS


def test_expired_token_returns_401(superadmin_client, mock_db):
    plain = "lu4_expiredtoken1234567890ab"
    row = _make_token_row(plain=plain, scopes=["import"])
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    mock_db.scalar.return_value = row

    r = superadmin_client.post(
        "/api/import",
        headers={"X-Api-Key": plain},
        json={
            "source": "test",
            "records": [{"product_name": "Sword", "seller": "Shop", "price": "100"}],
        },
    )
    assert r.status_code == 401
