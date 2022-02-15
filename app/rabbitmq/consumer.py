import sys
from logging import getLogger, StreamHandler, INFO
from os import environ
from socket import gaierror
from threading import Thread
from time import sleep
from uuid import uuid4

import pika
from pika.exceptions import (ChannelClosed, ConnectionClosedByBroker,
                             AMQPConnectionError, StreamLostError,
                             ChannelWrongStateError)

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
            self._action = "register"
        else:
            self._action = action
        self._base_URL = environ.get(action + "_base_URL")
        self._handler = publisher_handler
        self._stopped = False
        self._connection = None
        self._channel = None
        consumer_logger.info(f"Thread {self.name} started.")

    def _make_connection(self) -> (pika.BlockingConnection or None, bool):
        try:
            params = pika.URLParameters(
                f"amqp://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}")
            connection = pika.BlockingConnection(params)
        except (NameError, RuntimeError, gaierror, AMQPConnectionError) as e:
            consumer_logger.error(
                f"Failed to connect to RabbitMQ. {type(e)}: {e}")
            return None, False
        return connection, True

    def _set_connection(self) -> None or ConnectionError:
        for try_connect in range(10):
            self._connection, is_open = self._make_connection()
            if is_open:
                consumer_logger.info("publisher_handler connected to RabbitMQ")
                break
            else:
                if try_connect == 9:
                    raise ConnectionError("Couldn't connect to RabbitMQ.")
                sleep(5)

    def _callback(self, ch, method, properties, body) -> None:
        mail_address = body.decode()
        consumer_logger.info(
            f"Received {mail_address} from {self._queue_name}.")

        url_with_token = self._save_token_and_email(email=mail_address)
        message = {"email": mail_address, "URL": url_with_token}
        self._handler.publish(
            queue_name=self._queue_name + "_email",
            message=message,
            action=self._action)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def _save_token_and_email(self, email: str) -> str:
        token = uuid4().hex
        with SessionLocal() as db:
            action_id = db.query(Action.id).filter(
                Action.action == self._action).first()[0]
            token_data = Token(
                **{"token": token, "email": email, "action_id": action_id})
            db.add(token_data)
            db.commit()
        return f"{self._base_URL}/?email={email}&email_token={token}"

    def _set_queue(self) -> None:
        self._channel.queue_declare(queue=self._queue_name, durable=True)
        print(f"Waiting for messages from {self._queue_name}.")
        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(
            queue=self._queue_name,
            on_message_callback=self._callback,
            consumer_tag=self._action
        )

    def run(self) -> None:
        self._set_connection()
        self._channel = self._connection.channel()
        self._set_queue()

        while not self._stopped:
            try:
                consumer_logger.info(
                    f"Consumer started consuming. Thread:{self.name}")
                self._channel.start_consuming()
            except(ChannelWrongStateError, ChannelClosed) as e:
                consumer_logger.error(
                    f"Channel supposed to connect to RabbitMQ is closed."
                    f"{type(e)}:{e}. Thread:{self.name}")
                sleep(10)
                self._set_connection()
                self._channel = self._connection.channel()
                self._set_queue()
                consumer_logger.info(
                    f"Channel reconnected to RabbitMQ. Thread:{self.name}")
                continue

            except (ConnectionClosedByBroker, StreamLostError) as e:
                consumer_logger.error(
                    f"Connection with RabbitMQ was closed.{type(e)}:{e}. "
                    f"Thread:{self.name}")
                sleep(10)
                self._set_connection()
                self._channel = self._connection.channel()
                self._set_queue()
                consumer_logger.info(
                    f"Channel reconnected to RabbitMQ. Thread:{self.name}")
                continue

    def terminate_consume(self) -> None:
        self._stopped = True
        try:
            sys.exit(0)
        except SystemExit:
            consumer_logger.info(f"Thread for {self.name} was terminated.")
