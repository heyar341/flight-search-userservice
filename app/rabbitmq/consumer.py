import sys
from logging import getLogger, StreamHandler, INFO
from os import environ
from threading import Thread
from time import sleep
from uuid import uuid4

import pika

from app.database import SessionLocal
from app.models import Token, Action
from app.rabbitmq.publisher import PublisherHandler

consumer_logger = getLogger(__name__)
consumer_logger.setLevel(INFO)
consumer_logger.addHandler(StreamHandler(sys.stdout))


class ConsumerThread(Thread):
    USER = environ.get("RABBITMQ_USER")
    PASSWORD = environ.get("RABBITMQ_PASSWORD")
    HOST = environ.get("RABBITMQ_HOST")
    PORT = environ.get("RABBITMQ_PORT")

    def __init__(self, action: str, publisher_handler: PublisherHandler):
        super(ConsumerThread, self).__init__()
        self.daemon = True
        self.name = action

        self._queue_name = action
        if action == "pre_register":
            self.action = "register"
        else:
            self.action = action
        self.base_URL = environ.get(action + "_base_URL")
        self._handler = publisher_handler
        consumer_logger.info(f"Thread {self.name} started.")

    def make_connection(self) -> (pika.BlockingConnection or None, bool):
        try:
            params = pika.URLParameters(
                f"amqp://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}")
            connection = pika.BlockingConnection(params)
        except NameError as e:
            consumer_logger.error(
                f"Failed to connect to RabbitMQ. {type(e)}: {e}")
            return None, False
        except RuntimeError as e:
            consumer_logger.error(
                f"Failed to connect to RabbitMQ. {type(e)}: {e}")
            return None, False
        return connection, True

    def _callback(self, ch, method, properties, body) -> None:
        mail_address = body.decode()
        consumer_logger.info(f"Received {mail_address} from {self.action}.")

        url_with_token = self.save_token_and_email(email=mail_address)
        message = {"email": mail_address, "URL": url_with_token}
        self._handler.publish(
            queue_name=self._queue_name + "_email",
            message=message,
            action=self.action)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def save_token_and_email(self, email: str) -> str:
        token = uuid4().hex
        with SessionLocal() as db:
            action_id = db.query(Action.id).filter(
                Action.action == self.action).first()[0]
            token_data = Token(
                **{"token": token, "email": email, "action_id": action_id})
            db.add(token_data)
            db.commit()
        return f"{self.base_URL}/?email={email}&email_token={token}"

    def run(self) -> None:
        connection = None
        for try_connect in range(5):
            connection, is_open = self.make_connection()
            if is_open:
                break
            else:
                if try_connect == 4:
                    raise ConnectionError()
                sleep(5)
        channel = connection.channel()

        channel.queue_declare(queue=self._queue_name, durable=True)
        print(f"Waiting for messages from {self._queue_name}.")
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=self._queue_name,
            on_message_callback=self._callback,
            consumer_tag=self.action
        )

        channel.start_consuming()

    def terminate_consume(self):
        try:
            sys.exit(0)
        except SystemExit:
            consumer_logger.info(f"Thread for {self.name} was terminated.")
