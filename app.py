# -*- encoding: utf8 -*-

"""
@klemmari\_bot _query_ \- Select and send an image from Google image search results with the given query

/img _query_ \- Post the first image from Google image search with the given query \("I'm Feeling Lucky"\)

/puppu _input_ \- Generate a "puppulause" from the given input

/inspis \- Generate a random inspirational image

/ask \- Ask questions or talk to VavaBot

/reset \- Reset VavaBot conversation history

/subscribe \- Subscribe chat to bargain alerts

/unsubscribe \- Unsubscribe chat from bargain alerts

/help \- Show this help message
"""  # noqa

import json
import random
import threading
import time
import urllib
from logging.config import dictConfig

import jwt
import openai
import requests
import sentry_sdk
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from sentry_sdk.integrations.flask import FlaskIntegration

import chatbot
import settings
import tgbot
from chats import Chat, db

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

app = Flask(__name__)

# DB Setup
conn_str = settings.DATABASE_URL
app.config["SQLALCHEMY_DATABASE_URI"] = conn_str
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.app_context().push()
db.create_all()

# Sentry setup
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FlaskIntegration()],
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)

bot = tgbot.TgbotConnection(settings.TELEGRAM_TOKEN)


error_images = [
    "https://github.com/klemmari1/tg_vava_bot/raw/master/images/error.png",
]

not_found_images = [
    "https://github.com/klemmari1/tg_vava_bot/raw/master/images/not_found.png",
]

not_found_captions = [
    "Your query did not match any images.",
]


OPENAI_CONVERSATION_HISTORY = {}


def reset_conversation_history(chat_ids: list = []):
    if chat_ids == []:
        chat_ids = settings.OPENAI_CHAT_IDS

    for openai_chat_id in chat_ids:
        OPENAI_CONVERSATION_HISTORY[openai_chat_id] = chatbot.ChatBot(chatbot.prompt)


reset_conversation_history()


def poll_for_updates():
    with app.app_context():
        update_id = 0

        while True:
            # Send a request to the server with the last ID we received
            response = bot.makeRequest("getUpdates", offset=update_id, timeout=20)

            # If we received new data, process it
            if response and response.status_code == 200:
                response_json = response.json()
                updates = response_json.get("result", None)

                for update in updates:
                    app.logger.info("Incoming request:" + str(update))
                    if "inline_query" in update:
                        inline_query = update["inline_query"]
                        handle_inline_query(inline_query)
                    else:
                        msg = update.get("message", update.get("edited_message", None))
                        handle_message(msg)

                    update_id = int(update.get("update_id", 0)) + 1
            else:
                # If the server did not respond with new data, wait for a while before sending another request
                time.sleep(5)


@app.route("/" + settings.TELEGRAM_HOOK, methods=["POST"])
def webhook_handler():
    if request.method == "POST":
        message = request.get_json(force=True)
        app.logger.info("Incoming request:" + str(message))
        if "inline_query" in message:
            inline_query = message["inline_query"]
            handle_inline_query(inline_query)
        else:
            msg = message.get("message", message.get("edited_message", None))
            handle_message(msg)
    return "ok"


@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    app.logger.info("Host URL: " + request.host_url)
    s = bot.setWebhook(request.host_url + settings.TELEGRAM_HOOK)
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"


@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    response = bot.makeRequest("deleteWebhook")
    if response:
        return "webhook delete ok"
    else:
        return "webhook delete failed"


def decode_auth_token(auth_token):
    try:
        jwt.decode(auth_token, settings.EXTERNAL_ENDPOINT_KEY, algorithms=["HS256"])
    except Exception as e:
        app.logger.exception(f"Exception while decoding auth token: {str(e)}")
        return False
    return True


@app.route("/send_alert", methods=["POST"])
def send_alert():
    auth_token = request.headers.get("Authorization")
    auth_succesfull = decode_auth_token(auth_token)
    if not auth_succesfull:
        return Response("Access denied!", 401)

    message = request.data

    chats = Chat.query.all()
    chat_ids = [chat.id for chat in chats]
    for chat_id in chat_ids:
        response = bot.sendMessage(
            chat_id=chat_id,
            text=message,
            disable_web_page_preview=True,
        )
        if response:
            app.logger.info("SEND ALERT:")
            app.logger.info(response.status_code)
            app.logger.info(response.content)

    return "OK"


@app.route("/")
def index():
    return "Hello World!"


def handle_message(msg):
    if msg and "text" in msg:
        text = msg["text"]
        commands = {
            "/img": cmd_img,
            "/puppu": cmd_puppu,
            "/inspis": cmd_inspis,
            "/ask": cmd_ask,
            "/reset": cmd_reset,
            "/subscribe": cmd_subscribe,
            "/unsubscribe": cmd_unsubscribe,
            "/help": cmd_help,
            "/vtest": test_img,
        }
        try:
            cmdname, args = text.split(" ", 1)
        except ValueError:
            cmdname = text
            args = ""
        if "@" in cmdname:
            cmdname = cmdname.split("@")[0]
        if cmdname in commands:
            chat_id = str(msg["chat"]["id"])
            app.logger.info("command: " + str(cmdname))
            app.logger.info("args: " + str(args))
            app.logger.info("chat id: " + chat_id)
            commands[cmdname](args, chat_id)


def handle_inline_query(inline_query):
    if "query" in inline_query:
        query = inline_query["query"]
        if query != "":
            inline_query_id = inline_query["id"]
            app.logger.info("inline query id: " + str(inline_query_id))
            app.logger.info("inline query args: " + str(query))
            items = google_search(query)
            if isinstance(items, list):
                response = bot.sendInlineResponse(
                    inline_query_id=inline_query_id, items=items
                )
                if response and response.status_code != 200:
                    app.logger.info(
                        "Error sending inline response: " + str(response.text)
                    )
            else:
                app.logger.info(
                    "Error getting images from Google search. Response: " + str(items)
                )


def cmd_img(query, chat_id):
    # If empty query
    if not query:
        return
    # Get results with query
    items = google_search(query)
    # TODO check daily search quota
    if items == -1:
        # Send image about daily limit reached
        daily_limit(query, chat_id)
        return
    elif items == -2:
        return
    elif items is None:
        # Send image about image not found
        not_found(query, chat_id)
        return
    # Send image that does not give client errors
    for item in items:
        url = item["link"]
        response = bot.sendPhoto(chat_id=chat_id, photo=url)
        if response and response.status_code != 200:
            app.logger.info(str(response))
        else:
            break


def cmd_puppu(query, chat_id):
    query = urllib.parse.quote_plus(query, safe="", encoding="utf-8", errors=None)
    url = "http://puppulausegeneraattori.fi/?avainsana=" + query
    response = urllib.request.urlopen(url, timeout=settings.REQUEST_TIMEOUT).read()
    soup = BeautifulSoup(response, "html.parser")
    text = soup.find("p", {"class": "lause"})
    text = text.contents[0]
    app.logger.info(text)
    bot.sendMessage(chat_id=chat_id, text=text)


def cmd_inspis(query, chat_id):
    url = "https://inspirobot.me/api?generate=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5)"
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/50.0.2661.102 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=settings.REQUEST_TIMEOUT)
    url = response.content.decode("utf-8")
    app.logger.info(url)
    bot.sendPhoto(chat_id=chat_id, photo=url)


def cmd_help(query, chat_id):
    help_text = __doc__
    bot.sendMessage(
        chat_id=chat_id,
        text=help_text,
        parse_mode="MarkdownV2",
        disable_notification=True,
    )


def cmd_subscribe(query, chat_id):
    chat_id = str(chat_id)
    chat = Chat.query.get(chat_id)
    if not chat:
        chat = Chat(id=chat_id)
        chat.subscribe()

        text = "Subscribed to bargain alerts!"
    else:
        text = "Chat already subscribed to bargain alerts!"

    bot.sendMessage(
        chat_id=chat_id,
        text=text,
    )


def cmd_unsubscribe(query, chat_id):
    chat_id = str(chat_id)
    chat = Chat.query.get(chat_id)
    if chat:
        chat.unsubscribe()

        text = "Unsubscribed from bargain alerts!"
    else:
        text = "Chat is not subscribed to bargain alerts!"
    bot.sendMessage(
        chat_id=chat_id,
        text=text,
    )


def google_search(search_terms):
    # Use Google Custom Search API to find an image
    try:
        searchType = "image"
        gl = "fi"
        url = (
            "https://www.googleapis.com/customsearch/v1?q="
            + search_terms
            + "&key="
            + settings.GOOGLE_SEARCH_KEY
            + "&cx="
            + settings.GOOGLE_SEARCH_CX
            + "&searchType="
            + searchType
            + "&gl="
            + gl
        )
        contents = requests.get(url, timeout=settings.REQUEST_TIMEOUT).text
        json_response = json.loads(contents)
        if "items" in json_response:
            return json_response["items"]
        elif "error" in json_response:
            if "message" in json_response["error"]:
                if "billing" in json_response["error"]["message"]:
                    return -1
        return None
    except Exception as e:
        app.logger.exception("Exception while processing google search: " + str(e))
        return -2


def test_img(query, chat_id):
    if query == "1":
        app.logger.info(daily_limit(query, chat_id))
    elif query == "2":
        app.logger.info(not_found(query, chat_id))


def daily_limit(query, chat_id):
    return bot.sendPhoto(
        chat_id=chat_id,
        photo=random.choice(error_images),
        caption="You've reached the daily search limit of Google API :(",
    )


def not_found(query, chat_id):
    return bot.sendPhoto(
        chat_id=chat_id,
        photo=random.choice(not_found_images),
        caption=random.choice(not_found_captions),
    )


def cmd_ask(query: str, chat_id: str):
    if chat_id not in settings.OPENAI_CHAT_IDS:
        bot.sendMessage(
            chat_id=chat_id,
            text="GPT-4 not enabled in this chat",
        )
        return

    gpt_response, total_tokens = chatbot.query(
        query,
        OPENAI_CONVERSATION_HISTORY[chat_id],
        app.logger,
        max_turns=5,
    )

    bot.sendMessage(
        chat_id=chat_id,
        text=gpt_response,
    )

    if total_tokens >= 5000 or gpt_response == "Token limit reached":
        reset_conversation_history([chat_id])


def cmd_reset(query: str, chat_id: str):
    if chat_id not in settings.OPENAI_CHAT_IDS:
        bot.sendMessage(
            chat_id=chat_id,
            text="GPT-4 not enabled in this chat",
        )
        return

    reset_conversation_history([chat_id])

    bot.sendMessage(
        chat_id=chat_id,
        text="GPT-4 chat history reset",
    )


thread = threading.Thread(target=poll_for_updates)
thread.start()

if __name__ == "__main__":
    app.run(debug=True, port=settings.PORT)
