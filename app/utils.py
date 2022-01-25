from hashlib import sha256
from os import environ


def hash_password(password: str):
    salt = environ["SALT"]
    return sha256(password + salt)
