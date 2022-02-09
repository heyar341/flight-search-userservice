import datetime
import uvicorn
from fastapi import FastAPI, status, Depends, HTTPException, Cookie, Request
from fastapi.responses import Response, RedirectResponse
import threading
from anyio._backends._asyncio import WorkerThread
from logging import getLogger
from sqlalchemy.orm import Session
from os import environ

from schemas import (UserCreateReq, UserOut, NameUpdate, EmailUpdate,
                     PasswordUpdate)
from utils import hash_password, compare_hash, check_token
import models
from database import get_db
from rabbitmq import publish_message, ConsumerThread
from access_token import create_access_token, verify_access_token
from forms import LoginForm

app = FastAPI()
logger = getLogger("uvicorn")


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


@app.get("/user_data", status_code=status.HTTP_200_OK, response_model=UserOut)
def get_user(req: Request, db: Session = Depends(get_db)) -> UserOut:
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
    user = db.query(models.User.username, models.User.email).filter(
        models.User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ユーザー情報が取得できませんでした。")
    return user


@app.patch("/update/username", status_code=status.HTTP_200_OK)
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


@app.patch("/update/email", status_code=status.HTTP_200_OK)
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


@app.patch("/update/password", status_code=status.HTTP_200_OK)
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


@app.post("/login", status_code=status.HTTP_200_OK)
def login(
        form_data: LoginForm = Depends(),
        db: Session = Depends(get_db)) -> Response:
    user = db.query(
        models.User.id, models.User.username, models.User.password).filter(
        models.User.email == form_data.email).first()
    error_response = RedirectResponse(url=environ.get("LOGIN_URL"))
    error_response.set_cookie(
        key="error_msg",
        value="Fail",
        max_age=1,
        path="/accounts/login",
        domain=environ.get("APP_DOMAIN"),
        httponly=True)
    if not user:
        return error_response

    password_matched = compare_hash(form_data.password, user.password)
    if not password_matched:
        return error_response
    token = create_access_token({"user_id": user.id})
    logger.info(f"User id:{user.id} , username:{user.username} logged in.")
    success_response = RedirectResponse(url=environ.get("HOME_URL"))
    success_response.set_cookie(
        key="access_token",
        value=token,
        max_age=3600 * 24 * 30,
        path="/",
        domain=environ.get("APP_DOMAIN"),
        httponly=True)
    return success_response


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

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
