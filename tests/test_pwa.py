"""Tests del PWA: service worker, manifest e íconos."""


def test_service_worker_served_from_root(client):
    res = client.get("/sw.js")
    assert res.status_code == 200
    assert "javascript" in res.headers["Content-Type"]
    assert res.headers.get("Service-Worker-Allowed") == "/"


def test_manifest_served(client):
    res = client.get("/static/manifest.json")
    assert res.status_code == 200


def test_icons_served(client):
    assert client.get("/static/icons/icon-192.png").status_code == 200
    assert client.get("/static/icons/icon-512.png").status_code == 200
