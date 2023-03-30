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
import logging
import random
import threading
import time
import urllib

import jwt
import openai
import requests
import sentry_sdk
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from sentry_sdk.integrations.flask import FlaskIntegration

import settings
import tgbot
from chats import Chat, db

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
        OPENAI_CONVERSATION_HISTORY[openai_chat_id] = [
            {"role": "system", "content": "You are a helpful assistant named VavaBot."},
        ]


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
                    logging.info("Incoming request:" + str(update))
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
        logging.info("Incoming request:" + str(message))
        if "inline_query" in message:
            inline_query = message["inline_query"]
            handle_inline_query(inline_query)
        else:
            msg = message.get("message", message.get("edited_message", None))
            handle_message(msg)
    return "ok"


@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    logging.info("Host URL: " + request.host_url)
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
        logging.exception(f"Exception while decoding auth token: {str(e)}")
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
            logging.info("SEND ALERT:")
            logging.info(response.status_code)
            logging.info(response.content)

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
            logging.info("command: " + str(cmdname))
            logging.info("args: " + str(args))
            logging.info("chat id: " + str(msg["chat"]["id"]))
            commands[cmdname](args, msg["chat"]["id"])


def handle_inline_query(inline_query):
    if "query" in inline_query:
        query = inline_query["query"]
        if query != "":
            inline_query_id = inline_query["id"]
            logging.info("inline query id: " + str(inline_query_id))
            logging.info("inline query args: " + str(query))
            items = google_search(query)
            if isinstance(items, list):
                response = bot.sendInlineResponse(
                    inline_query_id=inline_query_id, items=items
                )
                if response and response.status_code != 200:
                    logging.info("Error sending inline response: " + str(response.text))
            else:
                logging.info(
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
            logging.info(str(response))
        else:
            break


def cmd_puppu(query, chat_id):
    query = urllib.parse.quote_plus(query, safe="", encoding="utf-8", errors=None)
    url = "http://puppulausegeneraattori.fi/?avainsana=" + query
    response = urllib.request.urlopen(url, timeout=settings.REQUEST_TIMEOUT).read()
    soup = BeautifulSoup(response, "html.parser")
    text = soup.find("p", {"class": "lause"})
    text = text.contents[0]
    logging.info(text)
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
    logging.info(url)
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
        logging.exception("Exception while processing google search: " + str(e))
        return -2


def test_img(query, chat_id):
    if query == "1":
        logging.info(daily_limit(query, chat_id))
    elif query == "2":
        logging.info(not_found(query, chat_id))


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


def request_gpt(query: str, chat_id: str):
    openai.api_key = settings.OPENAI_API_KEY

    OPENAI_CONVERSATION_HISTORY[chat_id].append({"role": "user", "content": query})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4", messages=OPENAI_CONVERSATION_HISTORY[chat_id]
        )
        response_text = response["choices"][0]["message"]["content"]
    except Exception as e:
        logging.warning(f"Exception while requesting GPT: {str(e)}")
        return "Error occurred while requesting GPT"

    OPENAI_CONVERSATION_HISTORY[chat_id].append(
        {"role": "assistant", "content": response_text}
    )

    return response_text


def cmd_ask(query: str, chat_id: str):
    if chat_id not in settings.OPENAI_CHAT_IDS:
        bot.sendMessage(
            chat_id=chat_id,
            text="GPT-4 not enabled in this chat",
        )
        return
    gpt_response = request_gpt(query, chat_id)
    bot.sendMessage(
        chat_id=chat_id,
        text=gpt_response,
    )


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
