from datetime import datetime, timedelta
from logging import getLogger
from os import environ

from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError

from app.schemas import JWTData

SECRET_KEY = environ.get("JWT_SECRET_KEY")
ALGORITHM = environ.get("JWT_ALGORITHM")
logger = getLogger("uvicorn")


def create_access_token(data: dict) -> str:
    token_dict = data.copy()
    token_dict["exp"] = datetime.utcnow() + timedelta(days=30)
    encoded_jwt = jwt.encode(token_dict, SECRET_KEY, ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> (JWTData, str):
    try:
        payload = jwt.decode(token, SECRET_KEY, [ALGORITHM])
        user_id: str = payload.get("user_id")
        if not user_id:
            logger.warning(
                f"Invalid token was sent. Couldn't get user_id from decoded "
                f"access_token")
            return None, "認証情報に不正があります。"
        token_data = JWTData(user_id=user_id)
    except JWTError or JWTClaimsError as e:
        logger.warning(f"Invalid token was sent.{e}")
        return None, "認証情報に不正があります。"
    except ExpiredSignatureError:
        return None, "再ログインが必要です。"

    return token_data, None
