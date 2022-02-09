import uvicorn
from fastapi import FastAPI
import threading
from anyio._backends._asyncio import WorkerThread
from logging import getLogger

from rabbitmq import ConsumerThread
from routers import register, update, show, auth

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


if __name__ == "__main__":
    actions = ("pre_register", "update_email")

    for action in actions:
        thread = ConsumerThread(action=action)
        thread.start()

    # debug時必要ないので、一時的にコメントアウト
    # uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
