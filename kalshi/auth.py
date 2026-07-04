"""Kalshi RSA-PSS authentication helpers."""

import base64
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def load_private_key(path: Path) -> rsa.RSAPrivateKey:
    """Load an RSA private key from a PEM file."""
    with open(path, "rb") as f:
        data = f.read()
    key = serialization.load_pem_private_key(data, password=None, backend=default_backend())
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("Private key must be an RSA key")
    return key


def sign_request(private_key: rsa.RSAPrivateKey, timestamp: str, method: str, path: str) -> str:
    """Sign a Kalshi request.

    The signed message is: timestamp + HTTP_METHOD + path_without_query
    Example: "1715793600000GET/trade-api/v2/portfolio/orders"
    """
    # Strip query string if present
    path_without_query = path.split("?")[0]
    message = f"{timestamp}{method.upper()}{path_without_query}".encode("utf-8")

    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")
