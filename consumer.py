import json
import os

import pika

from app import app, bot
from chats import Chat

# ENV variables
RABBIT_MQ_URL = os.getenv("RABBIT_MQ_URL", "")


def callback(ch, method, properties, body):
    with app.app_context():
        data = json.loads(body)
        message = data["message"]

        if properties.content_type == "io-tech":
            chats = Chat.query.all()
            chat_ids = [chat.id for chat in chats]
            for chat_id in chat_ids:
                response = bot.sendMessage(
                    chat_id=chat_id,
                    text=message,
                    disable_web_page_preview=True,
                )
                print("SEND ALERT:")
                print(response.status_code)
                print(response.content)

    ch.basic_ack(delivery_tag=method.delivery_tag)


params = pika.URLParameters(RABBIT_MQ_URL)

connection = pika.BlockingConnection(params)

channel = connection.channel()

channel.queue_declare(queue="sale_alerts")

channel.basic_consume(queue="sale_alerts", on_message_callback=callback)

print("Started consuming")

channel.start_consuming()
