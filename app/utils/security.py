"""
Password hashing helpers.

Uses the `bcrypt` library directly (NOT passlib). passlib's CryptContext
has a known incompatibility with bcrypt>=4.1 (it reads
`bcrypt.__about__.__version__`, an attribute removed in bcrypt 4.1+),
which raises AttributeError the first time a password is hashed or
verified. Calling bcrypt directly avoids that fragile dependency chain
entirely.
"""
from __future__ import annotations

import bcrypt

_BCRYPT_ROUNDS = 12


def hash_password(plain_password: str) -> str:
    if plain_password is None:
        plain_password = ""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(_BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not plain_password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed/legacy hash — treat as non-matching rather than crashing.
        return False
