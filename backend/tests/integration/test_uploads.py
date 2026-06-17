# tests/integration/test_uploads.py
"""Tests del módulo uploads (Cloudinary proxy). El SDK se mockea: no se pega a la red."""
import io
from unittest.mock import patch

import pytest

from app.core.config import settings

pytestmark = pytest.mark.integration


def _configurar_cloudinary(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", "demo")
    monkeypatch.setattr(settings, "CLOUDINARY_API_KEY", "123")
    monkeypatch.setattr(settings, "CLOUDINARY_API_SECRET", "secret")


_FAKE_UPLOAD = {
    "secure_url": "https://res.cloudinary.com/demo/image/upload/x.jpg",
    "public_id": "foodstore/productos/x",
    "width": 800, "height": 600, "format": "jpg", "resource_type": "image",
}


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"0" * 32


def test_subir_admin_ok(client, admin_auth_headers, monkeypatch):
    _configurar_cloudinary(monkeypatch)
    with patch("cloudinary.uploader.upload", return_value=_FAKE_UPLOAD) as up:
        resp = client.post(
            "/api/v1/uploads/imagen",
            files={"file": ("x.png", io.BytesIO(_png_bytes()), "image/png")},
            data={"folder": "productos"},
            headers=admin_auth_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["secure_url"].startswith("https://")
    assert data["public_id"]
    assert up.called


def test_subir_formato_invalido_422(client, admin_auth_headers, monkeypatch):
    _configurar_cloudinary(monkeypatch)
    resp = client.post(
        "/api/v1/uploads/imagen",
        files={"file": ("x.gif", io.BytesIO(b"GIF89a"), "image/gif")},
        data={"folder": "productos"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 422


def test_subir_cliente_forbidden(client, client_auth_headers, monkeypatch):
    _configurar_cloudinary(monkeypatch)
    resp = client.post(
        "/api/v1/uploads/imagen",
        files={"file": ("x.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"folder": "productos"},
        headers=client_auth_headers,
    )
    assert resp.status_code == 403


def test_subir_sin_configurar_400(client, admin_auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", "")
    monkeypatch.setattr(settings, "CLOUDINARY_API_KEY", "")
    monkeypatch.setattr(settings, "CLOUDINARY_API_SECRET", "")
    resp = client.post(
        "/api/v1/uploads/imagen",
        files={"file": ("x.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"folder": "productos"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 400


def test_eliminar_admin_ok(client, admin_auth_headers, monkeypatch):
    _configurar_cloudinary(monkeypatch)
    with patch("cloudinary.uploader.destroy", return_value={"result": "ok"}) as dl:
        resp = client.delete(
            "/api/v1/uploads/imagen/foodstore%2Fproductos%2Fx",
            headers=admin_auth_headers,
        )
    assert resp.status_code == 204
    assert dl.called


def test_eliminar_cliente_forbidden(client, client_auth_headers):
    resp = client.delete(
        "/api/v1/uploads/imagen/foodstore%2Fproductos%2Fx",
        headers=client_auth_headers,
    )
    assert resp.status_code == 403
