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
        message = request.get_json(force=True)
        message = message['message']
        handleMessage(message)
    return 'ok'

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook(os.environ["URL"] + os.environ["HOOK"])
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
            '/img': cmdImg,
            '/vtest': testImg
        }
        try:
            if '/img ' in text:
                cmdname = '/img'
                args = text.split('/img ')[1]
            else:
                cmdname, args = text.split(' ', 1)
        except ValueError:
            cmdname = text
            args = ''
        if cmdname in commands:
            print("command: " + str(cmdname))
            print("args: " + str(args))
            print("chat id: " + str(msg['chat']['id']))
            commands[cmdname](args, msg['chat']['id'])

def cmdImg(query, chat_id):
    #Search for image with the query
    url = get_image_url(query)
    if(url == -1):
        #Send image about daily limit reached
        num = randint(0, 5)
        filename = "images/" + str(num) + ".jpg"
        with open(filename, 'rb') as f:
            bot.sendPhoto(chat_id=chat_id, photo=f, caption="You done up reached my daily search limit again :(")
    elif(url != None):
        #If image found
        bot.sendPhoto(chat_id=chat_id, photo=url)

def testImg(query, chat_id):
    num = randint(0, 5)
    filename = "images/" + str(num) + ".jpg"
    with open(filename, 'rb') as f:
        bot.sendPhoto(chat_id=chat_id, photo=f, caption="You done up reached my daily search limit again :(")

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
    except urllib2.HTTPError as e:
        json_err = e.fp.read()
        print(json_err)
        if("error" in json_err):
            if("message" in json_err["error"]):
                if("billing" in json_err["error"]["message"]):
                    return -1
    except Exception as e:
        print("Exception: " + str(e))


if __name__ == '__main__':
    app.run(debug=True)
