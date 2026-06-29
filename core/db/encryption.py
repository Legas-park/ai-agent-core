"""
API 키·토큰 Fernet 암호화.

CONFIG_ENCRYPTION_KEY는 `SecretEncryptor.generate_key()`로 생성한 값을 사용합니다.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(ValueError):
    """암호화/복호화 실패."""


class SecretEncryptor:
    """Fernet 기반 시크릿 암·복호화."""

    def __init__(self, key: str):
        if not key or not key.strip():
            raise EncryptionError(
                "CONFIG_ENCRYPTION_KEY가 비어 있습니다. "
                "python -c \"from core.db.encryption import SecretEncryptor; "
                "print(SecretEncryptor.generate_key())\" 로 생성하세요."
            )
        try:
            self._fernet = Fernet(key.strip().encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise EncryptionError("CONFIG_ENCRYPTION_KEY 형식이 올바르지 않습니다 (Fernet key).") from exc

    @staticmethod
    def generate_key() -> str:
        """새 Fernet 키를 생성합니다."""
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None:
            return ""
        if plaintext == "":
            return ""
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise EncryptionError("복호화 실패 — CONFIG_ENCRYPTION_KEY가 일치하지 않습니다.") from exc
