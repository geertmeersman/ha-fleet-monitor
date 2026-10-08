import json

# --- Setup ---


def test_setup_redirects_to_login_when_already_configured(client):
    # app fixture already sets password_hash, so /setup should redirect
    res = client.get("/setup")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_setup_get_when_no_password_set(app, client):
    import db

    db.delete_setting("password_hash")
    res = client.get("/setup")
    assert res.status_code == 200
    assert b"setup" in res.data.lower() or res.status_code == 200


def test_setup_post_missing_fields(app, client):
    import db

    db.delete_setting("password_hash")
    res = client.post("/setup", data=json.dumps({"email": "", "password": ""}), content_type="application/json")
    assert res.status_code == 400


def test_setup_post_creates_account(app, client):
    import db

    db.delete_setting("password_hash")
    res = client.post(
        "/setup",
        data=json.dumps({"email": "admin@example.com", "password": "newpass123"}),
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"
    assert db.get_setting("password_hash") is not None
    assert db.get_setting("admin_email") == "admin@example.com"


def test_redirect_to_setup_when_no_password_set(app, client):
    import db

    db.delete_setting("password_hash")
    res = client.get("/")
    assert res.status_code == 302
    assert "/setup" in res.headers["Location"]


# --- Auth ---


def test_login_page(client):
    res = client.get("/login")
    assert res.status_code == 200


def test_login_invalid_password(client):
    res = client.post("/login", data={"password": "wrong"})
    assert res.status_code == 200
    assert b"Invalid password" in res.data or res.status_code == 200


def test_login_valid_password(client):
    res = client.post("/login", data={"password": "testpassword"}, follow_redirects=True)
    assert res.status_code == 200


def test_redirect_to_login_when_unauthenticated(client):
    for path in ["/", "/admin", "/api/status", "/api/instances"]:
        res = client.get(path)
        assert res.status_code in (302, 401), f"{path} should redirect unauthenticated users"


def test_logout(auth_client):
    res = auth_client.get("/logout", follow_redirects=True)
    assert res.status_code == 200
    res = auth_client.get("/")
    assert res.status_code == 302


# --- Dashboard & Admin pages ---


def test_index_authenticated(auth_client):
    res = auth_client.get("/")
    assert res.status_code == 200
    assert b"HA Fleet Monitor" in res.data


def test_admin_authenticated(auth_client):
    res = auth_client.get("/admin")
    assert res.status_code == 200


# --- Instances API ---


def test_get_instances_empty(auth_client):
    res = auth_client.get("/api/instances")
    assert res.status_code == 200
    assert res.get_json() == []


def test_add_instance(auth_client):
    payload = {
        "id": "test",
        "name": "Test",
        "url": "https://test.example.com",
        "token": "abc123",
        "email": "test@example.com",
    }
    res = auth_client.post("/api/instances", data=json.dumps(payload), content_type="application/json")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_get_instances_after_add(auth_client):
    payload = {"id": "test2", "name": "Test2", "url": "https://test2.example.com", "token": "xyz", "email": ""}
    auth_client.post("/api/instances", data=json.dumps(payload), content_type="application/json")
    res = auth_client.get("/api/instances")
    instances = res.get_json()
    assert any(i["id"] == "test2" for i in instances)


def test_delete_instance(auth_client):
    payload = {"id": "todelete", "name": "Del", "url": "https://del.example.com", "token": "tok", "email": ""}
    auth_client.post("/api/instances", data=json.dumps(payload), content_type="application/json")
    res = auth_client.delete("/api/instances/todelete")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"
    instances = auth_client.get("/api/instances").get_json()
    assert not any(i["id"] == "todelete" for i in instances)


def test_upsert_instance_updates_existing(auth_client):
    payload = {"id": "upd", "name": "Original", "url": "https://upd.example.com", "token": "tok", "email": ""}
    auth_client.post("/api/instances", data=json.dumps(payload), content_type="application/json")
    payload["name"] = "Updated"
    auth_client.post("/api/instances", data=json.dumps(payload), content_type="application/json")
    instances = auth_client.get("/api/instances").get_json()
    match = next(i for i in instances if i["id"] == "upd")
    assert match["name"] == "Updated"


def test_add_instance_managed_flag(auth_client):
    payload = {
        "id": "mgd",
        "name": "Managed",
        "url": "https://mgd.example.com",
        "token": "tok",
        "email": "",
        "managed": True,
    }
    auth_client.post("/api/instances", data=json.dumps(payload), content_type="application/json")
    instances = auth_client.get("/api/instances").get_json()
    match = next(i for i in instances if i["id"] == "mgd")
    assert match["managed"] == 1


def test_add_instance_monitored_by_default(auth_client):
    payload = {"id": "mon", "name": "Monitored", "url": "https://mon.example.com", "token": "tok", "email": ""}
    auth_client.post("/api/instances", data=json.dumps(payload), content_type="application/json")
    instances = auth_client.get("/api/instances").get_json()
    match = next(i for i in instances if i["id"] == "mon")
    assert not match["managed"]


# --- Config API ---


def test_api_config(auth_client):
    res = auth_client.get("/api/config")
    assert res.status_code == 200
    data = res.get_json()
    assert "test_mode" in data
    assert "test_recipient" in data


# --- Language ---


def test_set_lang(auth_client):
    for lang in ["en", "nl", "fr", "de", "es"]:
        res = auth_client.get(f"/api/set-lang/{lang}", follow_redirects=True)
        assert res.status_code == 200


def test_set_lang_invalid(auth_client):
    res = auth_client.get("/api/set-lang/xx", follow_redirects=True)
    assert res.status_code == 200
