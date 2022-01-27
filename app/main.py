import datetime
import uvicorn
from fastapi import FastAPI, status, Depends, HTTPException
from schemas import UserCreate, NameUpdate, EmailUpdate, PasswordUpdate
from utils import hash_password, compare_hash
import models
from database import get_db
from sqlalchemy.orm import Session
from rabbitmq import publish_message
from logging import getLogger

app = FastAPI()
logger = getLogger("uvicorn")

REGISTER_MAIL_QUEUE_NAME = "register_mail_queue"
UPDATE_MAIL_QUEUE_NAME = "update_mail_queue"


@app.post("/", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)) -> None:
    user_exists = db.query(models.User).filter(
        models.User.email == user.email).first()
    if user_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"メールアドレス{user.email} はすでに登録されています。")
    user.password = hash_password(user.password)
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    publish_message(user.email, REGISTER_MAIL_QUEUE_NAME)


@app.patch("/username/{user_id}", status_code=status.HTTP_200_OK)
def update_username(user_id: int, request: NameUpdate,
                    db: Session = Depends(get_db)) -> None:
    db_query = db.query(models.User).filter(
        models.User.username == request.current_username,
        models.User.id == user_id)
    user_exists = db_query.first()
    if not user_exists:
        logger.warning(
            f"Invalid update request came to /username/{user_id}. Request's "
            f"current_username was {request.current_username}, but didn't "
            f"matched user:{user_id}'s username.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"不正なユーザー情報が送信されました。")
    db_query.update({models.User.username: request.new_username,
                     models.User.updated_at: datetime.datetime.now()},
                    synchronize_session=False)
    db.commit()
    logger.info(f"User id:{user_id} updated username")


@app.patch("/email/{user_id}", status_code=status.HTTP_200_OK)
def update_email(user_id: int, request: EmailUpdate,
                 db: Session = Depends(get_db)) -> None:
    db_query = db.query(models.User).filter(
        models.User.email == request.current_email, models.User.id == user_id)
    user_exists = db_query.first()
    if not user_exists:
        logger.warning(
            f"Invalid update request came to /email/{user_id}. Request's "
            f"current_email was {request.current_email}, but didn't matched "
            f"user:{user_id}'s email.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"不正なユーザー情報が送信されました。")
    email_exists = db.query(models.User).filter(
        models.User.email == request.new_email).first()
    if email_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{request.new_email} はすでに登録されています。")

    db_query.update({models.User.email: request.new_email,
                     models.User.updated_at: datetime.datetime.now()},
                    synchronize_session=False)
    db.commit()
    publish_message(request.new_email, UPDATE_MAIL_QUEUE_NAME)
    logger.info(f"User id:{user_id} updated email")


@app.patch("/password/{user_id}", status_code=status.HTTP_200_OK)
def update_password(user_id: int, request: PasswordUpdate,
                    db: Session = Depends(get_db)) -> None:
    db_query = db.query(models.User).filter(models.User.id == user_id)
    user = db_query.first()
    password_matched = compare_hash(
        request.current_password,
        user.password)
    if not password_matched:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="入力されたパスワードが間違っています。")
    db_query.update(
        {models.User.password: hash_password(request.new_password),
         models.User.updated_at: datetime.datetime.now()},
        synchronize_session=False)
    db.commit()
    logger.info(f"User id:{user_id} updated password")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
