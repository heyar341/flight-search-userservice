import json
import logging
import sys
from logging import getLogger
from os import environ
from socket import gaierror
from time import sleep

import pika
from pika.exceptions import StreamLostError, AMQPConnectionError

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
        self._set_connection()
        self._publishers = {}

    def _make_connection(self) -> (pika.BlockingConnection or None, bool):
        try:
            params = pika.URLParameters(
                f"amqp://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}")
            connection = pika.BlockingConnection(params)
        except (NameError, RuntimeError, gaierror, AMQPConnectionError) as e:
            publisher_logger.error(
                f"Failed to connect to RabbitMQ. {type(e)}: {e}")
            return None, False
        return connection, True

    def _set_connection(self) -> None or ConnectionError:
        for try_connect in range(10):
            self._connection, is_open = self._make_connection()
            if is_open:
                publisher_logger.info("publisher_handler connected to RabbitMQ")
                break
            else:
                if try_connect == 9:
                    raise ConnectionError("Couldn't connect to RabbitMQ.")
                sleep(5)

    def publish(self, queue_name: str, message: dict, action: str) -> None:
        if self._connection.is_closed:
            self._set_connection()
            if self._publishers:
                for publisher in self._publishers.values():
                    publisher.refresh_connection(self._connection)

        if action not in self._publishers:
            publisher = Publisher(
                queue_name=queue_name,
                connection=self._connection)
            self._publishers[action] = publisher
        try:
            self._publishers[action].publish_message(message=message)
        except StreamLostError:
            # heartbeatによりRabbitMQがconnectionを閉じた場合half-openの状態になる。
            # self._connection.is_closedはFalseとなるが、
            # 実際にはconnectionは閉じているためStreamLostErrorとなる。
            self._set_connection()
            if self._publishers:
                for publisher in self._publishers.values():
                    publisher.refresh_connection(self._connection)
            if action not in self._publishers:
                publisher = Publisher(
                    queue_name=queue_name,
                    connection=self._connection)
                self._publishers[action] = publisher
            self._publishers[action].publish_message(message=message)

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
            f"{message.get('email')}.")

    def refresh_connection(self, connection: pika.BlockingConnection) -> None:
        self._connection = connection


publisher_handler = PublisherHandler()
