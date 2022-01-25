import pika
from os import environ
from logging import getLogger

USER = environ.get("RABBITMQ_USER")
PASSWORD = environ.get("RABBITMQ_PASSWORD")
HOST = environ.get("RABBITMQ_HOST")
PORT = environ.get("RABBITMQ_PORT")

logger = getLogger("uvicorn")


def publish_message(email: str, queue_name: str) -> None:
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

    message = email.encode()
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
        ))
    logger.info(f"User service sent email message to RabbiMQ. email: {email}")
    connection.close()
