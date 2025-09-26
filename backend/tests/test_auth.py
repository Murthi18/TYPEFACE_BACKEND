# backend/tests/test_auth.py
import json

def test_signup_then_me_and_logout(client):

    email = "alice13@example.com"
    # Sign up
    res = client.post(
        "/api/auth/signup",
        data=json.dumps({"name":"Alice1","email":email,"password":"Secret_123"}),
        content_type="application/json",
    )
    assert res.status_code == 201
    payload = res.get_json()
    assert payload["user"]["email"] == email

    # Session cookie present → /me works
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == email

    # Logout clears session
    out = client.post("/api/auth/logout")
    assert out.status_code == 200
    assert out.get_json()["ok"] is True

    # After logout → /me has no user
    me2 = client.get("/api/auth/me")
    assert me2.status_code == 200
    assert me2.get_json()["user"] is None

def test_duplicate_email_rejected(client):
    for _ in range(2):
        res = client.post(
            "/api/auth/signup",
            json={"name":"Bob","email":"bob@example.com","password":"pw"},
        )
    assert res.status_code == 409
    assert "already in use" in res.get_json()["error"].lower()

def test_login_success_and_fail(client):
    # Prepare a user
    client.post("/api/auth/signup", json={"name":"C","email":"c@x.com","password":"Pw_12345"})
    # Good login
    ok = client.post("/api/auth/login", json={"email":"c@x.com","password":"Pw_12345"})
    assert ok.status_code == 200
    assert ok.get_json()["user"]["email"] == "c@x.com"

    # Bad login
    bad = client.post("/api/auth/login", json={"email":"c@x.com","password":"nope"})
    assert bad.status_code == 401
