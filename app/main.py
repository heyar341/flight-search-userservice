import uvicorn
from fastapi import FastAPI, status, Depends, HTTPException
import threading
from anyio._backends._asyncio import WorkerThread
from logging import getLogger
from sqlalchemy.orm import Session

from schemas import UserCreateReq, LoginData
from utils import hash_password, compare_hash, check_token
import app.models as models
from database import get_db
from rabbitmq import publish_message, ConsumerThread
from access_token import create_access_token
from routers import update, show

logger = getLogger("uvicorn")
app = FastAPI()
app.include_router(show.router)
app.include_router(update.router)


@app.post("/register", status_code=status.HTTP_201_CREATED)
def create_user(req: UserCreateReq, db: Session = Depends(get_db)) -> None:
    user_data = req.user_data
    token_data = req.token_data
    exception = check_token(token=token_data.token, email=user_data.email,
                            req_action=token_data.action, db=db)
    if exception:
        raise exception

    user_exists = db.query(models.User).filter(
        models.User.email == user_data.email).first()
    if user_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"メールアドレス{user_data.email} "
                                   f"はすでに登録されています。")
    user_data.password = hash_password(user_data.password)
    new_user = models.User(**user_data.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    publish_message(message={"email": user_data.email},
                    queue_name="confirm_register_email")


@app.post("/login", status_code=status.HTTP_200_OK)
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


@app.on_event("shutdown")
def terminate_threads() -> None:
    for thread in threading.enumerate():
        if thread is threading.current_thread() or type(thread) == WorkerThread:
            continue
        thread.terminate_consume()


if __name__ == "__main__":
    actions = ("pre_register", "update_email")

    for action in actions:
        thread = ConsumerThread(action=action)
        thread.start()

    # debug時必要ないので、一時的にコメントアウト
    # uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
