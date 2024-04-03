# -*- encoding: utf8 -*-

"""
@klemmari\_bot _query_ — Select and send an image from Google image search results with the given query

/img _query_ — Post the first image from Google image search with the given query \("I'm Feeling Lucky"\)

/puppu _input_ — Generate a "puppulause" from the given input

/inspis — Generate a random inspirational image

/ask — Ask questions or talk to VavaBot

/reset — Reset VavaBot conversation history

/subscribe — Subscribe chat to bargain alerts

/unsubscribe — Unsubscribe chat from bargain alerts

/help — Show this help message
"""  # noqa

import asyncio
import json
import random
import threading
import urllib
from dataclasses import dataclass
from logging.config import dictConfig

import jwt
import requests
import sentry_sdk
import telegram
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from sentry_sdk.integrations.flask import FlaskIntegration
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultPhoto,
    Update,
)
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    TypeHandler,
)

import chatbot
import settings
from chats import Chat, db


@dataclass
class WebhookUpdate:
    """Simple dataclass to wrap a custom update type"""

    chat_id: int
    payload: str


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

bot = Application.builder().token(settings.TELEGRAM_TOKEN).build()

error_images = [
    "https://github.com/klemmari1/tg_vava_bot/raw/master/images/error.png",
]

not_found_images = [
    "https://github.com/klemmari1/tg_vava_bot/raw/master/images/not_found.png",
]

not_found_captions = [
    "Your query did not match any images.",
]

CATEGORIES = {
    1: "Tekniikka ja elektroniikka",
    2: "Työkalut ja rakennustarvikkeet",
    3: "Koti ja sisustus",
    4: "Vaatetus",
    5: "Harrastusvälineet ja tarvikkeet",
    6: "Autot ja ajoneuvot",
    7: "Ruoka ja juomat",
    8: "Kirjat ja lehdet",
    9: "Peliaiheiset tuotteet",
    10: "Tietokoneen komponentit",
    11: "Muut",
}

OPENAI_CONVERSATION_HISTORY = {}

SELECTED_CATEGORIES = {}


def reset_conversation_history(chat_ids: list = []):
    app.logger.info(f"Resetting conversation history of chat IDs: {chat_ids}")
    if not chat_ids:
        chat_ids = settings.OPENAI_CHAT_IDS

    for openai_chat_id in chat_ids:
        OPENAI_CONVERSATION_HISTORY[openai_chat_id] = chatbot.ChatBot(chatbot.prompt)


reset_conversation_history()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    app.logger.error("Exception while handling an update:", exc_info=context.error)
    sentry_sdk.capture_exception(context.error)


# def poll_for_updates():
#     with app.app_context():
#         update_id = 0
#
#         while True:
#             # Send a request to the server with the last ID we received
#             response = bot.makeRequest("getUpdates", offset=update_id, timeout=20)
#
#             # If we received new data, process it
#             if response and response.status_code == 200:
#                 response_json = response.json()
#                 updates = response_json.get("result", None)
#
#                 for update in updates:
#                     app.logger.info("Incoming request:" + str(update))
#                     if "inline_query" in update:
#                         inline_query = update["inline_query"]
#                         handle_inline_query(inline_query)
#                     else:
#                         msg = update.get("message", update.get("edited_message", None))
#                         handle_message(msg)
#
#                     update_id = int(update.get("update_id", 0)) + 1
#             else:
#                 # If the server did not respond with new data, wait for a while before sending another request
#                 time.sleep(5)
#

# @app.route("/" + settings.TELEGRAM_HOOK, methods=["POST"])
# def webhook_handler():
#     if request.method == "POST":
#         message = request.get_json(force=True)
#         app.logger.info("Incoming request:" + str(message))
#         if "inline_query" in message:
#             inline_query = message["inline_query"]
#             handle_inline_query(inline_query)
#         else:
#             msg = message.get("message", message.get("edited_message", None))
#             handle_message(msg)
#     return "ok"


# @app.route("/set_webhook", methods=["GET"])
# def set_webhook():
#     app.logger.info("Host URL: " + request.host_url)
#     s = bot.setWebhook(request.host_url + settings.TELEGRAM_HOOK)
#     if s:
#         return "webhook setup ok"
#     else:
#         return "webhook setup failed"


# @app.route("/delete_webhook", methods=["GET"])
# def delete_webhook():
#     response = bot.makeRequest("deleteWebhook")
#     if response:
#         return "webhook delete ok"
#     else:
#         return "webhook delete failed"


async def send_message_to_chat(chat_id: int, text: str) -> None:
    await telegram.Bot(settings.TELEGRAM_TOKEN).send_message(
        chat_id=chat_id,
        text=text,
        disable_web_page_preview=True,
    )


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
    auth_successful = decode_auth_token(auth_token)
    if not auth_successful:
        return Response("Access denied!", 401)

    message = request.data.decode("utf-8")

    chats = Chat.query.all()
    chat_ids = [chat.id for chat in chats]
    for chat_id in chat_ids:
        # response = bot.sendMessage(
        #     chat_id=chat_id,
        #     text=message,
        #     disable_web_page_preview=True,
        # )
        # if response:
        #     app.logger.info("SEND ALERT:")
        #     app.logger.info(response.status_code)
        #     app.logger.info(response.content)
        asyncio.new_event_loop().run_until_complete(
            send_message_to_chat(int(chat_id), message)
        )

    return "OK"


@app.route("/")
def index():
    return "Hello World!"


# def handle_message(msg):
#     if msg and "text" in msg:
#         text = msg["text"]
#         commands = {
#             "/img": cmd_img,
#             "/puppu": cmd_puppu,
#             "/inspis": cmd_inspis,
#             "/ask": cmd_ask,
#             "/reset": cmd_reset,
#             "/subscribe": cmd_subscribe,
#             "/unsubscribe": cmd_unsubscribe,
#             "/help": cmd_help,
#             "/vtest": test_img,
#         }
#         try:
#             cmdname, args = text.split(" ", 1)
#         except ValueError:
#             cmdname = text
#             args = ""
#         if "@" in cmdname:
#             cmdname = cmdname.split("@")[0]
#         if cmdname in commands:
#             chat_id = str(msg["chat"]["id"])
#             app.logger.info("command: " + str(cmdname))
#             app.logger.info("args: " + str(args))
#             app.logger.info("chat id: " + chat_id)
#             commands[cmdname](args, chat_id)


async def handle_inline_query(update: Update, context: CallbackContext):
    query = update.inline_query.query
    query_id = update.inline_query.id
    if query != "":
        app.logger.info("inline query id: " + str(query_id))
        app.logger.info("inline query args: " + str(query))
        items = google_search(query)
        results = []
        if isinstance(items, list):
            # response = bot.sendInlineResponse(
            #     inline_query_id=inline_query_id, items=items
            # )
            for item in items:
                photo_url = item["link"]
                thumb_url = item["image"]["thumbnailLink"]
                results.append(
                    InlineQueryResultPhoto(
                        id=query_id,
                        photo_url=photo_url,
                        thumbnail_url=thumb_url,
                    )
                )
            await update.inline_query.answer(results)
    await update.inline_query.answer([])


async def cmd_img(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text(text="No query provided")
        return

    query = context.args[0]
    app.logger.info(f"Image query: {query}")

    # Get results with a query
    items = google_search(query)
    if items == -1:
        # Send image about daily limit reached
        await daily_limit(update, context)
    elif items == -2:
        await update.message.reply_text("Exception occurred")
    elif items is None:
        # Send image about image not found
        await not_found(update, context)
    # Send image that does not give client errors
    for item in items:
        url = item["link"]
        await update.message.reply_photo(url)
        # response = bot.sendPhoto(chat_id=chat_id, photo=url)
        # if response and response.status_code != 200:
        #    app.logger.info(str(response))
        # else:
        #    break


async def cmd_puppu(update: Update, context: CallbackContext):
    query = ""
    if context.args:
        query = context.args[0]
    app.logger.info(f"Puppu query: {query}")

    query = urllib.parse.quote_plus(query, safe="", encoding="utf-8", errors=None)
    url = "http://puppulausegeneraattori.fi/?avainsana=" + query
    response = urllib.request.urlopen(url, timeout=settings.REQUEST_TIMEOUT).read()
    soup = BeautifulSoup(response, "html.parser")
    text = soup.find("p", {"class": "lause"})
    text = text.contents[0]
    app.logger.info(text)
    # bot.sendMessage(chat_id=chat_id, text=text)
    await update.message.reply_text(text.text)


async def cmd_inspis(update: Update, context: CallbackContext):
    url = "https://inspirobot.me/api?generate=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5)"
                      "AppleWebKit/537.36 (KHTML, like Gecko)"
                      "Chrome/50.0.2661.102 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=settings.REQUEST_TIMEOUT)
    url = response.content.decode("utf-8")
    app.logger.info(url)
    # bot.sendPhoto(chat_id=chat_id, photo=url)
    await update.message.reply_photo(url)


async def cmd_help(update: Update, context: CallbackContext):
    help_text = __doc__
    app.logger.info("Sending help text")
    await update.message.reply_text(
        help_text,
        parse_mode="MarkdownV2",
        disable_notification=True,
    )
    # bot.sendMessage(
    #     chat_id=chat_id,
    #     text=help_text,
    #     parse_mode="MarkdownV2",
    #     disable_notification=True,
    # )


def get_category_keyboard():
    keyboard = []
    for idx, category in CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(category, callback_data=str(idx))])
    keyboard.append([InlineKeyboardButton("Tilaa", callback_data="tilaa")])
    return InlineKeyboardMarkup(keyboard)


async def button_callback(update: Update, context: CallbackContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat.id

    # Handle submission
    if query.data == "tilaa":
        selected_categories_text = ""
        selected_categories = []
        if user_id in SELECTED_CATEGORIES and SELECTED_CATEGORIES[user_id]:
            for idx in SELECTED_CATEGORIES[user_id]:
                category = CATEGORIES[int(idx)]
                selected_categories_text += f"*— {category}*\n"
                selected_categories.append(category)

        data = {
            "chat-id": chat_id,
            "selected-categories": selected_categories,
            "sub-type": "subscribe",
        }
        requests.post(
            f"{settings.TARJOUSHAUKKA_URL}/chat",
            json=data,
        )
        # chat = chats.Chat(
        #     str(chat_id),
        # )
        # chat.subscribe()
        del SELECTED_CATEGORIES[user_id]

        if not selected_categories_text:
            await query.edit_message_text(
                text="*Tilasit kaikki kategoriat*",
                parse_mode="MarkdownV2",
            )
        else:
            await query.edit_message_text(
                f"Tilasit kategoriat:\n{selected_categories_text}",
                parse_mode="MarkdownV2",
            )
        return

    # Track user selections
    if user_id not in SELECTED_CATEGORIES:
        SELECTED_CATEGORIES[user_id] = []

    if query.data not in SELECTED_CATEGORIES[user_id]:
        SELECTED_CATEGORIES[user_id].append(query.data)
    else:
        SELECTED_CATEGORIES[user_id].remove(query.data)

    # Update the keyboard to reflect current selections
    markup = await get_updated_keyboard(SELECTED_CATEGORIES[user_id])
    await query.edit_message_reply_markup(
        reply_markup=markup,
    )


async def get_updated_keyboard(selected):
    """Updates the keyboard based on the selected categories."""
    keyboard = []
    for idx, category in CATEGORIES.items():
        text = f"{category}" + (" ✅" if str(idx) in selected else "")
        keyboard.append([InlineKeyboardButton(text, callback_data=str(idx))])
    keyboard.append([InlineKeyboardButton("Tilaa", callback_data="tilaa")])
    return InlineKeyboardMarkup(keyboard)


async def cmd_subscribe(update: Update, context: CallbackContext):
    # chat_id = str(chat_id)
    # chat = Chat.query.get(chat_id)
    # if not chat:
    #     chat = Chat(id=chat_id)
    #     chat.subscribe()
    #
    #     text = "Subscribed to bargain alerts!"
    # else:
    #     text = "Chat already subscribed to bargain alerts!"
    #
    # bot.sendMessage(
    #     chat_id=chat_id,
    #     text=text,
    # )
    """Sends a message with the category selection attached."""
    await update.message.reply_text(
        "Valitse kategoriat joihin liittyen haluat tarjousviestejä\n"
        "Paina lopuksi *_Tilaa_*\n\n"
        "Paina vain *_Tilaa_* jos haluat tilata kaikki kategoriat\n",
        parse_mode="MarkdownV2",
        reply_markup=get_category_keyboard(),
    )


async def cmd_unsubscribe(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    chat = Chat.query.get(chat_id)
    if chat:
        chat.unsubscribe()
        text = "Unsubscribed from bargain alerts!"
    else:
        text = "Chat is not subscribed to bargain alerts!"
    # bot.sendMessage(
    #     chat_id=chat_id,
    #     text=text,
    # )
    await update.message.reply_text(text)


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


async def test_img(update: Update, context: CallbackContext):
    query = ""
    if context.args:
        query = context.args[0]

    app.logger.info(f"Image query: {query}")

    if query == "1":
        await daily_limit(update, context)
    await not_found(update, context)


async def daily_limit(update: Update, context: CallbackContext):
    await update.message.reply_photo(
        random.choice(error_images),
        "You've reached the daily search limit of Google API :(",
    )


# return bot.sendPhoto(
#     chat_id=chat_id,
#     photo=random.choice(error_images),
#     caption="You've reached the daily search limit of Google API :(",
# )


async def not_found(update: Update, context: CallbackContext):
    await update.message.reply_photo(random.choice(not_found_images))
    # return bot.sendPhoto(
    #     chat_id=chat_id,
    #     photo=random.choice(not_found_images),
    #     caption=random.choice(not_found_captions),
    # )


async def cmd_ask(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)

    query = ""
    if context.args:
        query = context.args[0]
    app.logger.info(f"Ask query: {query}")

    if not query:
        await update.message.reply_text("No question provided")
        return

    if chat_id not in settings.OPENAI_CHAT_IDS:
        # bot.sendMessage(
        #     chat_id=chat_id,
        #     text="GPT-4 not enabled in this chat",
        # )
        await update.message.reply_text("GPT-4 not enabled in this chat")
        return

    gpt_response = chatbot.query(
        query,
        OPENAI_CONVERSATION_HISTORY[chat_id],
        app.logger,
        max_turns=5,
    )

    # bot.sendMessage(
    #     chat_id=chat_id,
    #     text=gpt_response,
    # )
    await update.message.reply_text(gpt_response)

    if gpt_response == "Token limit reached":
        reset_conversation_history([chat_id])


async def cmd_reset(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    if chat_id not in settings.OPENAI_CHAT_IDS:
        # bot.sendMessage(
        #     chat_id=chat_id,
        #     text="GPT-4 not enabled in this chat",
        # )
        await update.message.reply_text("GPT-4 not enabled in this chat")
        return

    reset_conversation_history([chat_id])
    await update.message.reply_text("GPT-4 chat history reset")


async def logging_handler(update: Update, context: CallbackContext):
    app.logger.info(f"Received message: {str(update)}")


bot.add_handler(TypeHandler(Update, logging_handler), group=-1)

bot.add_handler(CommandHandler("subscribe", cmd_subscribe))
bot.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
bot.add_handler(CommandHandler("img", cmd_img))
bot.add_handler(CommandHandler("puppu", cmd_puppu))
bot.add_handler(CommandHandler("inspis", cmd_inspis))
bot.add_handler(CommandHandler("ask", cmd_ask))
bot.add_handler(CommandHandler("reset", cmd_reset))
bot.add_handler(CommandHandler("help", cmd_help))
bot.add_handler(CommandHandler("vtest", test_img))

bot.add_handler(InlineQueryHandler(handle_inline_query))

bot.add_handler(CallbackQueryHandler(button_callback))

bot.add_error_handler(error_handler)

threading.Thread(
    target=lambda: app.run(host="0.0.0.0", port=settings.PORT, debug=True, use_reloader=False)
).start()

bot.run_polling()
