import logging

import pika
from os import environ
from logging import getLogger
from threading import Thread
from uuid import uuid4
import sys
import json

from database import SessionLocal
from app.models import Token, Action

USER = environ.get("RABBITMQ_USER")
PASSWORD = environ.get("RABBITMQ_PASSWORD")
HOST = environ.get("RABBITMQ_HOST")
PORT = environ.get("RABBITMQ_PORT")

logger = getLogger("uvicorn")
system_logger = getLogger(__name__)
system_logger.setLevel(logging.INFO)
system_logger.addHandler(logging.StreamHandler(sys.stdout))


def publish_message(message: dict, queue_name: str) -> None:
    try:
        params = pika.URLParameters(f"amqp://{USER}:{PASSWORD}@{HOST}:{PORT}")
        connection = pika.BlockingConnection(params)
    except NameError as e:
        logger.error(f"Failed to connect to RabbitMQ. {type(e)}: {e}")
        return
    except RuntimeError as e:
        logger.error(f"Failed to connect to RabbitMQ. {type(e)}: {e}")
        return
    channel = connection.channel()

    channel.queue_declare(queue=queue_name, durable=True)

    msg = json.dumps(message).encode()
    channel.basic_publish(exchange='', routing_key=queue_name, body=msg,
                          properties=pika.BasicProperties(
                              delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
                          )

    logger.info(
        f"User service sent email message to RabbiMQ. email: "
        f"{message['email']}")
    connection.close()


class ConsumerThread(Thread):
    def __init__(self, action: str):
        super(ConsumerThread, self).__init__()
        self.daemon = True
        self.name = action

        self.queue_name = action
        if action == "pre_register":
            self.action = "register"
        else:
            self.action = action
        self.base_URL = environ.get(action + "_base_URL")
        system_logger.info(f"Thread {self.name} started.")

    def callback(self, ch, method, properties, body) -> None:
        mail_address = body.decode()
        logger.info(f"Received {mail_address} from {self.action}.")

        url_with_token = self.save_token_and_email(email=mail_address)
        message = {"email": mail_address, "URL": url_with_token}
        publish_message(message=message, queue_name=self.queue_name + "_email")

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
        try:
            params = pika.URLParameters(
                f"amqp://{USER}:{PASSWORD}@{HOST}:{PORT}")
            connection = pika.BlockingConnection(params)
        except NameError as e:
            logger.error(f"Failed to connect to RabbitMQ. {type(e)}: {e}")
            return
        except RuntimeError as e:
            logger.error(f"Failed to connect to RabbitMQ. {type(e)}: {e}")
            return
        channel = connection.channel()

        channel.queue_declare(queue=self.queue_name, durable=True)
        print(f"Waiting for messages from {self.queue_name}.")
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=self.queue_name, on_message_callback=self.callback,
            consumer_tag=self.action
        )

        channel.start_consuming()

    def terminate_consume(self):
        try:
            sys.exit(0)
        except SystemExit:
            logger.info(f"Thread for {self.name} was terminated.")
