#!/usr/bin/env python3
# -*- encoding: utf8 -*-

import os
import urllib2
import json
import telegram
from flask import Flask, request
from random import randint


app = Flask(__name__)

global bot
bot = telegram.Bot(token=os.environ["TOKEN"])

@app.route('/' + os.environ["HOOK"], methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        chat_id = update.message.chat.id
        text = update.message.text.encode('utf-8')

        commands = {
            '/img': cmdImg
        }
        try:
            cmdname, args = text.split(' ', 1)
        except ValueError:
            cmdname = text
            args = ''
        if cmdname in commands:
            commands[cmdname](args, chat_id)
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

def cmdImg(query, chat_id):
    #Get image and save in file
    flag = True
    idx = 0
    while flag:
        try:
            url = get_image_url(query, idx)
            if(url == None):
                break
            filename = "out" + str(randint(0, 10000000000000000)) + ".jpg"
            f = open(filename, 'wb')
            f.write(urllib2.urlopen(url).read())
            f.close()
            flag = False
        except urllib2.HTTPError:
            idx += 1

    if(flag == False):
        #Send image and remove saved file
        img = open(filename, 'rb')
        bot.sendPhoto(chat_id=chat_id, photo=img)
        img.close()
        os.remove(filename)

def get_image_url(search_term, idx):
    try:
        key = os.environ["G_KEY"]
        cx = os.environ["G_CX"]
        searchType = "image"
        gl = "fi"
        search_term = search_term.replace(" ", "+")
        url = "https://www.googleapis.com/customsearch/v1?q=" + search_term + "&key=" + key + "&cx=" + cx + "&searchType=" + searchType + "&gl=" + gl
        contents = urllib2.urlopen(url).read()
        j = json.loads(contents)
        return j["items"][idx]["link"]
    except Exception as e:
        print("Exception: " + str(e))


if __name__ == '__main__':
    app.run(debug=True)
