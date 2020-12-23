import json
import os
from threading import Thread

import pika

# ENV variables
ALERT_CHAT_IDS = os.getenv("ALERT_CHAT_IDS", "test, test").split(", ")

RABBIT_MQ_URL = os.getenv("RABBIT_MQ_URL", "")


def callback(ch, method, properties, body):
    from app import bot

    data = json.loads(body)
    message = data["message"]

    if properties.content_type == "sale_alert":
        for chat_id in ALERT_CHAT_IDS:
            response = bot.sendMessage(
                chat_id=chat_id,
                text=message,
            )
            print("SEND ALERT:")
            print(response.status_code)
            print(response.content)

    ch.basic_ack(delivery_tag=method.delivery_tag)


if RABBIT_MQ_URL:
    params = pika.URLParameters(RABBIT_MQ_URL)

    connection = pika.BlockingConnection(params)

    channel = connection.channel()

    channel.queue_declare(queue="tgbot")

    channel.basic_consume(queue="tgbot", on_message_callback=callback)

    thread = Thread(target=channel.start_consuming)
    thread.start()
