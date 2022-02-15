import json
import logging
import sys
from logging import getLogger
from os import environ
from time import sleep

import pika

publisher_logger = getLogger(__name__)
publisher_logger.setLevel(logging.INFO)
publisher_logger.addHandler(logging.StreamHandler(sys.stdout))


class PublisherHandler(object):
    USER = environ.get("RABBITMQ_USER")
    PASSWORD = environ.get("RABBITMQ_PASSWORD")
    HOST = environ.get("RABBITMQ_HOST")
    PORT = environ.get("RABBITMQ_PORT")

    def __init__(self):
        self._connection = None
        self.set_connection()
        self.publishers = {}

    def make_connection(self) -> (pika.BlockingConnection or None, bool):
        try:
            params = pika.URLParameters(
                f"amqp://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}")
            connection = pika.BlockingConnection(params)
        except NameError as e:
            publisher_logger.error(
                f"Failed to connect to RabbitMQ. {type(e)}: {e}")
            return None, False
        except RuntimeError as e:
            publisher_logger.error(
                f"Failed to connect to RabbitMQ. {type(e)}: {e}")
            return None, False
        return connection, True

    def set_connection(self):
        for try_connect in range(5):
            self._connection, is_open = self.make_connection()
            if is_open:
                publisher_logger.info("publisher_handler connected to RabbitMQ")
                break
            else:
                if try_connect == 4:
                    raise ConnectionError()
                sleep(5)

    def publish(self, queue_name: str, message: dict, action: str):
        if self._connection.is_closed:
            self.set_connection()
            if self.publishers:
                for publisher in self.publishers.values():
                    publisher.refresh_connection(self._connection)

        if action not in self.publishers:
            publisher = Publisher(
                queue_name=queue_name,
                connection=self._connection)
            self.publishers[action] = publisher
        self.publishers[action].publish_message(message=message)

        if action not in self.publishers:
            publisher = Publisher(
                queue_name=queue_name,
                connection=self._connection)
            self.publishers[action] = publisher
        self.publishers[action].publish_message(message=message)

    def terminate_connection(self) -> None:
        publisher_logger.info(
            "publisher_handler closed connection from RabbitMQ")
        self._connection.close()


class Publisher(object):
    def __init__(self, queue_name: str, connection: pika.BlockingConnection):
        self._queue_name = queue_name
        self._connection = connection
        self._channel = connection.channel()
        self._channel.queue_declare(queue=queue_name, durable=True)
        self._stopping = False

    def publish_message(self, message: dict) -> None:
        if not self._channel or self._channel.is_closed:
            self._channel = self._connection.channel()
            self._channel.queue_declare(queue=self._queue_name, durable=True)
        msg = json.dumps(message).encode()
        self._channel.basic_publish(
            exchange='',
            routing_key=self._queue_name,
            body=msg,
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
        )

        publisher_logger.info(
            f"User service sent email message to RabbiMQ. email: "
            f"{message.get('email')}")

    def refresh_connection(self, connection: pika.BlockingConnection):
        self._connection = connection


publisher_handler = PublisherHandler()
