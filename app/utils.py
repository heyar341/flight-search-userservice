from hashlib import sha256
from os import environ


def hash_password(password: str) -> hex:
    salt = environ.get("SALT")
    return sha256((password + salt).encode()).hexdigest()


def compare_hash(raw_password: str, hashed_password: str) -> bool:
    hashed = hash_password(raw_password)
    if hashed == hashed_password:
        return True
    else:
        return False
