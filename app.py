# -*- encoding: utf8 -*-

import os
import urllib2
import json
import tgbot
from flask import Flask, request
from random import randint


class GoogleImageBot:
    def __init__(self):
        self.update_offset = 0

    def handleUpdate(self, update):
        upid = update['update_id']
        try:
            msg = update['message']
        except Exception as e:
            print("Exception: " + str(e))
        else:
            self.handleMessage(msg)
        self.update_offset = upid + 1

    def handleMessage(self, msg):
        if 'text' in msg:
            text = msg['text']
            commands = {
                '/img': self.cmdImg
            }
            try:
                cmdname, args = text.split(' ', 1)
            except ValueError:
                cmdname = text
                args = ''
            if cmdname in commands:
                commands[cmdname](args, msg['chat'])

    def cmdImg(self, query, chat_id):
        #Get image and save in file
        flag = True
        idx = 0
        #Loop finding an image that does not give 403 Forbidden error
        while flag:
            try:
                url = self.get_image_url(query, idx)
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

    def get_image_url(self, search_term, idx):
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
                if(len(j["items"]) > idx):
                    return j["items"][idx]["link"]
            return None
        except Exception as e:
            print("Exception: " + str(e))


app = Flask(__name__)

global bot
global gimgbot
bot = tgbot.TgbotConnection(os.environ["TOKEN"])
gimgbot = GoogleImageBot()

@app.route('/' + os.environ["HOOK"], methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        updates = bot.getUpdates(offset=0, timeout=60)
        for update in updates:
            gimgbot.handleUpdate(update)
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


if __name__ == '__main__':
    app.run(debug=True)
