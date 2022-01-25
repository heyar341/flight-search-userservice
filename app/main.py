from fastapi import FastAPI, status, Depends
from schemas import UserCreate
from utils import hash_password
import models
from database import get_db
from sqlalchemy.orm import Session

app = FastAPI()


@app.post("/", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)) -> None:
    user.password = hash_password(user.password)
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
