from hashlib import sha256
from os import environ


def hash_password(password: str) -> hex:
    salt = environ.get("SALT")
    return sha256((password + salt).encode()).hexdigest()
