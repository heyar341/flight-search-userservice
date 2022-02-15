from datetime import datetime, timezone
from hashlib import sha256
from os import environ

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Token, Action


def hash_password(password: str) -> hex:
    salt = environ.get("SALT")
    return sha256((password + salt).encode()).hexdigest()


def compare_hash(raw_password: str, hashed_password: str) -> bool:
    hashed = hash_password(raw_password)
    if hashed == hashed_password:
        return True
    else:
        return False


def check_token(token: str, email: str, req_action: str,
                db: Session) -> HTTPException | None:
    auth_data = db.query(Token.email, Token.expires_at, Action.action).join(
        Action, Token.action_id == Action.id).filter(
        Token.token == token, Token.email == email).first()

    if not auth_data:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="認証情報が取得できませんでした。")

    email, expires_at, action = auth_data
    if action != req_action:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="認証情報が一致しません。")

    if datetime.now(timezone.utc) > expires_at:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                             detail="トークンの期限が切れています。")

    return None
