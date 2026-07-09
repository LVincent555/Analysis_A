"""Generate local security secrets for DEC-002 Level 1.5."""

from __future__ import annotations

import base64
import os
import secrets

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _fingerprint(public_key) -> str:
    der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashes.Hash(hashes.SHA256())
    digest.update(der)
    return base64.urlsafe_b64encode(digest.finalize()).decode("ascii").rstrip("=")


def main() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    escaped_private_pem = private_pem.replace("\n", "\\n")
    escaped_public_pem = public_pem.replace("\n", "\\n")

    print("# Backend .env")
    print(f"JWT_SECRET_KEY={secrets.token_urlsafe(48)}")
    print(f"MASTER_ENCRYPTION_KEY={base64.b64encode(os.urandom(32)).decode('ascii')}")
    print(f"INTERNAL_GATEWAY_SECRET={secrets.token_urlsafe(48)}")
    print("LOGIN_PUBLIC_KEY_ID=login-rsa-local-001")
    print(f"LOGIN_PRIVATE_KEY={escaped_private_pem}")
    print("REQUIRE_SECURE_LOGIN=true")
    print("ALLOW_INSECURE_DEV_KEYS=false")
    print()
    print("# Frontend .env")
    print("REACT_APP_SECURE_LOGIN_KEY_ID=login-rsa-local-001")
    print(f"REACT_APP_SECURE_LOGIN_PUBLIC_KEY={escaped_public_pem}")
    print(f"REACT_APP_SECURE_LOGIN_PUBLIC_KEY_FINGERPRINT={_fingerprint(public_key)}")
    print("REACT_APP_ALLOW_PLAINTEXT_LOGIN=false")


if __name__ == "__main__":
    main()
