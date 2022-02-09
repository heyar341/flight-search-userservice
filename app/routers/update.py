import datetime
from fastapi import status, Depends, HTTPException, Request, APIRouter
from logging import getLogger
from sqlalchemy.orm import Session

from app.schemas import NameUpdate, EmailUpdate, PasswordUpdate
from app.utils import hash_password, compare_hash
import app.models as models
from app.database import get_db
from app.rabbitmq import publish_message
from app.access_token import verify_access_token

router = APIRouter(prefix="/update")
logger = getLogger("uvicorn")


@router.patch("/username", status_code=status.HTTP_200_OK)
def update_username(
        update_data: NameUpdate,
        req: Request,
        db: Session = Depends(get_db)) -> HTTPException or None:
    access_token = req.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインしていません。")
    token_data, error = verify_access_token(access_token)
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error)
    db_query = db.query(models.User).filter(
        models.User.username == update_data.current_username,
        models.User.id == token_data.user_id)
    user_exists = db_query.first()
    if not user_exists:
        logger.warning(
            f"Invalid update request came to /update/username . Request's "
            f"current_username was {update_data.current_username}, but didn't "
            f"matched user:{token_data.user_id}'s username.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"不正なユーザー情報が送信されました。")
    db_query.update(
        {models.User.username: update_data.new_username,
         models.User.updated_at: datetime.datetime.now()},
        synchronize_session=False)
    db.commit()
    logger.info(f"User id:{token_data.user_id} updated username")


@router.patch("/email", status_code=status.HTTP_200_OK)
def update_email(
        update_data: EmailUpdate,
        req: Request,
        db: Session = Depends(get_db)) -> None:
    access_token = req.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインしていません。")
    token_data, error = verify_access_token(access_token)
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error)
    db_query = db.query(models.User).filter(
        models.User.email == update_data.current_email,
        models.User.id == token_data.user_id)
    user_exists = db_query.first()
    if not user_exists:
        logger.warning(
            f"Invalid update request came to /email/{token_data.user_id}. "
            f"Request's current_email was {update_data.current_email}, "
            f"but didn't matched user:{token_data.user_id}'s email.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"不正なユーザー情報が送信されました。")
    email_exists = db.query(models.User.email).filter(
        models.User.email == update_data.new_email).first()
    if email_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{update_data.new_email} はすでに登録されています。")

    db_query.update({models.User.email: update_data.new_email,
                     models.User.updated_at: datetime.datetime.now()},
                    synchronize_session=False)
    db.commit()
    publish_message(message={"email": update_data.new_email},
                    queue_name="update_email_email")
    logger.info(f"User id:{token_data.user_id} updated email")


@router.patch("/password", status_code=status.HTTP_200_OK)
def update_password(
        update_data: PasswordUpdate,
        req: Request,
        db: Session = Depends(get_db)) -> None:
    access_token = req.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインしていません。")
    token_data, error = verify_access_token(access_token)
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error)
    db_query = db.query(models.User).filter(
        models.User.id == token_data.user_id)
    user = db_query.first()
    password_matched = compare_hash(
        raw_password=update_data.current_password,
        hashed_password=user.password)
    if not password_matched:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="入力されたパスワードが間違っています。")
    db_query.update(
        {models.User.password: hash_password(update_data.new_password),
         models.User.updated_at: datetime.datetime.now()},
        synchronize_session=False)
    db.commit()
    logger.info(f"User id:{token_data.user_id} updated password")
