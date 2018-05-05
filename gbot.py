#!/usr/bin/env python3
# -*- encoding: utf8 -*-

import os
import urllib.request
import json
import telegram
from flask import Flask, request


app = Flask(__name__)

global bot
bot = telegram.Bot(token=os.environ["TOKEN"])

@app.route('/asd123jaa', methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        # retrieve the message in JSON and then transform it to Telegram object
        update = telegram.Update.de_json(request.get_json(force=True))

        chat_id = update.message.chat.id

        # Telegram understands UTF-8, so encode text for unicode compatibility
        text = update.message.text.encode('utf-8')

        # repeat the same message back (echo)
        bot.sendMessage(chat_id=chat_id, text=get_image_url(text))

    return 'ok'

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook('https://vavabot.herokuapp.com/asd123jaa')
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"

@app.route('/')
def index():
    return 'Hello World!'


def get_image_url(search_term):
    try:
        key = os.environ["G_KEY"]
        cx = os.environ["G_CX"]
        searchType = "image"
        search_term = search_term.replace(" ", "+")
        url = "https://www.googleapis.com/customsearch/v1?q=" + search_term + "&key=" + key + "&cx=" + cx + "&searchType=" + searchType
        contents = urllib.request.urlopen(url).read()
        j = json.loads(contents)
        return j["items"][0]["link"]
    except Exception as e:
        print("Exception: " + str(e))
