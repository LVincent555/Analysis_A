"""Identity crypto adapter wrapping the legacy AES helpers."""

from ....crypto.aes_handler import (
    AESCrypto,
    derive_key_from_password,
    generate_key,
    get_master_crypto,
)


class AesIdentityCryptoProvider:
    def generate_key(self) -> bytes:
        return generate_key()

    def encrypt_user_key(self, user_key: bytes) -> str:
        return get_master_crypto().encrypt_key(user_key)

    def encrypt_session_key_with_password(self, password: str, session_key: bytes) -> str:
        password_derived_key = derive_key_from_password(password)
        return AESCrypto(password_derived_key).encrypt_key(session_key)


identity_crypto_provider = AesIdentityCryptoProvider()
