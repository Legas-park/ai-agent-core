import pytest

from core.db.encryption import EncryptionError, SecretEncryptor


def test_generate_key_is_valid_fernet():
    key = SecretEncryptor.generate_key()
    enc = SecretEncryptor(key)
    assert enc.decrypt(enc.encrypt("secret")) == "secret"


def test_encrypt_decrypt_roundtrip():
    key = SecretEncryptor.generate_key()
    enc = SecretEncryptor(key)
    ciphertext = enc.encrypt("sk-test-api-key")
    assert ciphertext != "sk-test-api-key"
    assert enc.decrypt(ciphertext) == "sk-test-api-key"


def test_empty_plaintext_returns_empty():
    key = SecretEncryptor.generate_key()
    enc = SecretEncryptor(key)
    assert enc.encrypt("") == ""
    assert enc.decrypt("") == ""


def test_invalid_key_raises():
    with pytest.raises(EncryptionError):
        SecretEncryptor("not-a-valid-fernet-key")


def test_wrong_key_decrypt_raises():
    enc1 = SecretEncryptor(SecretEncryptor.generate_key())
    enc2 = SecretEncryptor(SecretEncryptor.generate_key())
    token = enc1.encrypt("secret")
    with pytest.raises(EncryptionError):
        enc2.decrypt(token)
