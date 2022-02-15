from logging import getLogger

from fastapi import status, Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session

import app.models as models
from app.access_token import create_access_token
from app.database import get_db
from app.schemas import LoginData
from app.utils import compare_hash

router = APIRouter(prefix="/auth")
logger = getLogger("uvicorn")


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
        login_data: LoginData,
        db: Session = Depends(get_db)) -> HTTPException or dict:
    user = db.query(
        models.User.id, models.User.username, models.User.password).filter(
        models.User.email == login_data.email).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="入力されたパスワードが間違っています。")

    password_matched = compare_hash(login_data.password, user.password)
    if not password_matched:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="入力されたパスワードが間違っています。")
    access_token = create_access_token({"user_id": user.id})
    logger.info(f"User id:{user.id} , username:{user.username} logged in.")

    return {"access_token": access_token}
