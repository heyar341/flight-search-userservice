import threading
from logging import getLogger

from anyio._backends._asyncio import WorkerThread
from fastapi import FastAPI

from app.rabbitmq.consumer import ConsumerThread
from app.rabbitmq.publisher import publisher_handler
from app.routers import register, update, show, auth

logger = getLogger("uvicorn")

app = FastAPI()
app.include_router(show.router)
app.include_router(update.router)
app.include_router(register.router)
app.include_router(auth.router)


@app.on_event("shutdown")
def terminate_threads() -> None:
    for thread in threading.enumerate():
        if thread is threading.current_thread() or type(thread) == WorkerThread:
            continue
        thread.terminate_consume()

    publisher_handler.terminate_connection()


if __name__ == "__main__":
    actions = ("pre_register", "update_email")

    for action in actions:
        consumer_thread = ConsumerThread(
            action=action,
            publisher_handler=publisher_handler)
        consumer_thread.start()

    # debug時必要ないので、一時的にコメントアウト
    # uvicorn.run("main:app", host="0.0.0.0", port=5000)
