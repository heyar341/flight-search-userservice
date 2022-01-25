from fastapi import FastAPI, status, Depends, HTTPException
from schemas import UserCreate
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
                            detail=f"{user.email} is already registerd")
    user.password = hash_password(user.password)
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    publish_message(user.email, REGISTER_MAIL_QUEUE_NAME)
