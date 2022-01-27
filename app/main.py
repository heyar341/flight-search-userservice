from fastapi import FastAPI, status, Depends, HTTPException
from schemas import UserCreate, UserOut
from utils import hash_password
import models
from database import get_db
from sqlalchemy.orm import Session
from rabbitmq import publish_message

app = FastAPI()

REGISTER_MAIL_QUEUE_NAME = "register_mail_queue"


@app.post("/", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)) -> None:
    user_exists = db.query(models.User).filter(
        models.User.email == user.email).first()
    if user_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{user.email} is already registered")
    user.password = hash_password(user.password)
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    publish_message(user.email, REGISTER_MAIL_QUEUE_NAME)


@app.get("/{user_id}", status_code=status.HTTP_200_OK, response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"ユーザー情報が取得できませんでした。")
    return user
