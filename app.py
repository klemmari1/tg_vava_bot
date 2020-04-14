# -*- encoding: utf8 -*-

import os
import urllib
import requests
import json
import tgbot
import random
from flask import Flask, request
from bs4 import BeautifulSoup


app = Flask(__name__)

bot = tgbot.TgbotConnection(os.environ["TOKEN"])

error_images = [
    "https://miro.medium.com/max/1400/1*pUEZd8z__1p-7ICIO1NZFA.png",
]

not_found_images = [
    "https://howfix.net/wp-content/uploads/2018/02/sIaRmaFSMfrw8QJIBAa8mA-article.png",
]

not_found_captions = [
    "Your query did not match any images.",
]


@app.route("/" + os.environ["HOOK"], methods=["POST"])
def webhook_handler():
    if request.method == "POST":
        message = request.get_json(force=True)
        if "inline_query" in message:
            inline_query = message["inline_query"]
            handleInlineQuery(inline_query)
        else:
            msg = message["message"]
            handleMessage(msg)
    return "ok"


@app.route("/set_webhook", methods=["GET", "POST"])
def set_webhook():
    print("Host URL: " + request.host_url)
    s = bot.setWebhook(request.host_url + os.environ["HOOK"])
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"


@app.route("/")
def index():
    return "Hello World!"


def handleMessage(msg):
    if "text" in msg:
        text = msg["text"]
        commands = {"/img": cmdImg, "/puppu": cmdPuppu, "/vtest": testImg}
        try:
            cmdname, args = text.split(" ", 1)
        except ValueError:
            cmdname = text
            args = ""
        if cmdname in commands:
            print("command: " + str(cmdname))
            print("args: " + str(args))
            print("chat id: " + str(msg["chat"]["id"]))
            commands[cmdname](args, msg["chat"]["id"])


def handleInlineQuery(inline_query):
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


def cmdImg(query, chat_id):
    # If empty query
    if not query:
        return
    # Get results with query
    items = google_search(query)
    # TODO check daily search quota
    if items == -1:
        # Send image about daily limit reached
        dailyLimit(query, chat_id)
        return
    elif items == -2:
        return
    elif items == None:
        # Send image about image not found
        notFound(query, chat_id)
        return
    # Send image that does not give client errors
    for item in items:
        url = item["link"]
        response = bot.sendPhoto(chat_id=chat_id, photo=url)
        if response.status_code != 200:
            print(str(response))
        else:
            break


def cmdPuppu(query, chat_id):
    query = urllib.parse.quote_plus(query, safe="", encoding="utf-8", errors=None)
    url = "http://puppulausegeneraattori.fi/?avainsana=" + query
    response = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(response, "html5lib")
    text = soup.find("p", {"class": "lause"})
    text = text.contents[0]
    print(text)
    bot.sendMessage(chat_id=chat_id, text=text)


def google_search(search_terms):
    # Use Google Custom Search API to find an image
    try:
        key = os.environ["G_KEY"]
        cx = os.environ["G_CX"]
        searchType = "image"
        gl = "fi"
        url = (
            "https://www.googleapis.com/customsearch/v1?q="
            + search_terms
            + "&key="
            + key
            + "&cx="
            + cx
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


def testImg(query, chat_id):
    if query == "1":
        print(dailyLimit(query, chat_id))
    elif query == "2":
        print(notFound(query, chat_id))


def dailyLimit(query, chat_id):
    return bot.sendPhoto(
        chat_id=chat_id,
        photo=random.choice(error_images),
        caption="You've reached the daily search limit of Google API :(",
    )


def notFound(query, chat_id):
    return bot.sendPhoto(
        chat_id=chat_id,
        photo=random.choice(not_found_images),
        caption=random.choice(not_found_captions),
    )


if __name__ == "__main__":
    app.run(debug=True)
