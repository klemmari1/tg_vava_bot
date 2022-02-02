# -*- encoding: utf8 -*-

"""
@klemmari\_bot _query_ \- Select and send an image from Google image search results with the given query

/img _query_ \- Post the first image from Google image search with the given query \("I'm Feeling Lucky"\)

/puppu _input_ \- Generate a "puppulause" from the given input

/inspis \- Generate a random inspirational image

/subscribe \- Subscribe chat to sale alerts

/unsubscribe \- Unsubscribe chat from sale alerts

/help \- Show this help message
"""  # noqa

import json
import random
import urllib

import jwt
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


@app.route("/" + settings.TELEGRAM_HOOK, methods=["POST"])
def webhook_handler():
    if request.method == "POST":
        message = request.get_json(force=True)
        print("Incoming request:" + str(message))
        if "inline_query" in message:
            inline_query = message["inline_query"]
            handle_inline_query(inline_query)
        else:
            msg = message.get("message", message.get("edited_message", None))
            handle_message(msg)
    return "ok"


@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    print("Host URL: " + request.host_url)
    s = bot.setWebhook(request.host_url + settings.TELEGRAM_HOOK)
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"


def decode_auth_token(auth_token):
    try:
        jwt.decode(auth_token, settings.EXTERNAL_ENDPOINT_KEY, algorithms=["HS256"])
    except Exception as e:
        print(str(e))
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
        print("SEND ALERT:")
        print(response.status_code)
        print(response.content)

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
            print("command: " + str(cmdname))
            print("args: " + str(args))
            print("chat id: " + str(msg["chat"]["id"]))
            commands[cmdname](args, msg["chat"]["id"])


def handle_inline_query(inline_query):
    if "query" in inline_query:
        query = inline_query["query"]
        if query != "":
            inline_query_id = inline_query["id"]
            print("inline query id: " + str(inline_query_id))
            print("inline query args: " + str(query))
            items = google_search(query)
            if isinstance(items, list):
                response = bot.sendInlineResponse(
                    inline_query_id=inline_query_id, items=items
                )
                if response.status_code != 200:
                    print("Error sending inline response: " + str(response.text))
            else:
                print(
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
        if response.status_code != 200:
            print(str(response))
        else:
            break


def cmd_puppu(query, chat_id):
    query = urllib.parse.quote_plus(query, safe="", encoding="utf-8", errors=None)
    url = "http://puppulausegeneraattori.fi/?avainsana=" + query
    response = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(response, "html.parser")
    text = soup.find("p", {"class": "lause"})
    text = text.contents[0]
    print(text)
    bot.sendMessage(chat_id=chat_id, text=text)


def cmd_inspis(query, chat_id):
    url = "https://inspirobot.me/api?generate=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5)"
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/50.0.2661.102 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    url = response.content.decode("utf-8")
    print(url)
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

        text = "Subscribed to sale alerts!"
    else:
        text = "Chat already subscribed to sale alerts!"

    bot.sendMessage(
        chat_id=chat_id,
        text=text,
    )


def cmd_unsubscribe(query, chat_id):
    chat_id = str(chat_id)
    chat = Chat.query.get(chat_id)
    if chat:
        chat.unsubscribe()

        text = "Unsubscribed from sale alerts!"
    else:
        text = "Chat is not subscribed to sale alerts!"
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
        contents = requests.get(url).text
        json_response = json.loads(contents)
        if "items" in json_response:
            return json_response["items"]
        elif "error" in json_response:
            if "message" in json_response["error"]:
                if "billing" in json_response["error"]["message"]:
                    return -1
        return None
    except urllib.error.HTTPError as e:
        err = e.fp.read()
        print(str(err))
    except Exception as e:
        print("Exception: " + str(e))
        return -2


def test_img(query, chat_id):
    if query == "1":
        print(daily_limit(query, chat_id))
    elif query == "2":
        print(not_found(query, chat_id))


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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
