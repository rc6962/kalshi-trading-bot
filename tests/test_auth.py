"""Tests for Kalshi RSA-PSS authentication."""

import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kalshi.auth import load_private_key, sign_request


def _generate_test_key(path: Path) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(pem)


def test_load_private_key() -> None:
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
        path = Path(f.name)
    try:
        _generate_test_key(path)
        key = load_private_key(path)
        assert key is not None
        assert key.key_size == 2048
    finally:
        path.unlink(missing_ok=True)


def test_sign_request() -> None:
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
        path = Path(f.name)
    try:
        _generate_test_key(path)
        key = load_private_key(path)
        sig = sign_request(key, "1234567890000", "GET", "/trade-api/v2/portfolio/balance")
        assert isinstance(sig, str)
        assert len(sig) > 0
    finally:
        path.unlink(missing_ok=True)
