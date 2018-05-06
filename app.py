# -*- encoding: utf8 -*-

import os
import urllib2
import json
import tgbot
from flask import Flask, request
from random import randint


app = Flask(__name__)

global bot
bot = tgbot.TgbotConnection(os.environ["TOKEN"])

@app.route('/' + os.environ["HOOK"], methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        update = request.get_json(force=True)
        msg = update['message']
        handleMessage(msg)
    return 'ok'

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook('https://vavabot.herokuapp.com/' + os.environ["HOOK"])
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"

@app.route('/')
def index():
    return 'Hello World!'


def handleMessage(msg):
    if 'text' in msg:
        text = msg['text']
        commands = {
            '/img': cmdImg
        }
        try:
            cmdname, args = text.split(' ', 1)
        except ValueError:
            cmdname = text
            args = ''
        if cmdname in commands:
            commands[cmdname](args, msg['chat']['id'])

def cmdImg(query, chat_id):
    url = get_image_url(query)
    #Send image if found
    if(url != None):
        bot.sendPhoto(chat_id=chat_id, photo=url)

def get_image_url(search_term):
    #Use Google Custom Search API to find an image
    try:
        key = os.environ["G_KEY"]
        cx = os.environ["G_CX"]
        searchType = "image"
        gl = "fi"
        search_term = search_term.replace(" ", "+")
        url = "https://www.googleapis.com/customsearch/v1?q=" + search_term + "&key=" + key + "&cx=" + cx + "&searchType=" + searchType + "&gl=" + gl
        contents = urllib2.urlopen(url).read()
        j = json.loads(contents)
        if("items" in j):
            return j["items"][0]["link"]
        return None
    except Exception as e:
        print("Exception: " + str(e))



if __name__ == '__main__':
    app.run(debug=True)
