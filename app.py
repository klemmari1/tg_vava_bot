# -*- encoding: utf8 -*-

import os
import urllib2
import json
import tgbot
import random
from flask import Flask, request


app = Flask(__name__)

bot = tgbot.TgbotConnection(os.environ["TOKEN"])

error_images = ["https://cdnb.artstation.com/p/assets/images/images/001/993/973/large/benjamin-eberhard-sad-robot.jpg?1455679192",
                "http://img03.deviantart.net/43d5/i/2016/063/8/4/detective_sad_robot_by_spikesthecat-d9tv8se.png",
                "https://c1.staticflickr.com/3/2735/4262821422_b9b5a523c6.jpg",
                "https://musewb.files.wordpress.com/2012/10/5152157159_5ba65100a9_z.jpg"
                "https://fsmedia.imgix.net/83/3a/80/8b/8f3c/427e/aac2/99891d289d7c/the-robot-sophia-makes-an-angry-face-during-an-on-stage-interview.png?auto=format%2Ccompress&w=700"]

not_found_images = ["http://cdn.funnyand.com/wp-content/uploads/2014/03/404-PagenotfoundLOL_20140325-300x300.jpg",
                    "http://www.profitguide.com/wp-content/uploads/2013/09/google-not-found.jpg",
                    "https://i.imgflip.com/11fjj7.jpg",
                    "https://sd.keepcalm-o-matic.co.uk/i/error-404-meme-not-found.png"]

not_found_captions = ["You're a special snowflake, aren't you? No image found!",
                      "No image found!",
                      "Sry, no image",
                      "Cannot find images with this query!",
                      "Googl does not hav dis",
                      "No images with this query!",
                      "Where image? Not in internet",
                      "Hmm.. Cannot find this",
                      "Not found on google.. Maybe you can put it there?",
                      "Too weird query. Cannot find"]

@app.route('/' + os.environ["HOOK"], methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        message = request.get_json(force=True)
        message = message['message']
        handleMessage(message)
    return 'ok'

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    print("Host URL: " + request.host_url)
    s = bot.setWebhook(request.host_url + os.environ["HOOK"])
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
        text = text.encode('utf-8')
        commands = {
            '/img': cmdImg,
            '/vtest': testImg
        }
        try:
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
    #TODO check daily search quota
    if(url == -1):
        #Send image about daily limit reached
        dailyLimit(query, chat_id)
    elif(url != None):
        #If image found
        bot.sendPhoto(chat_id=chat_id, photo=url)
    elif(url == None):
        notFound(query, chat_id)

def testImg(query, chat_id):
    if query == "1":
        print(dailyLimit(query, chat_id))
    elif query == "2":
        print(notFound(query, chat_id))

def dailyLimit(query, chat_id):
    return bot.sendPhoto(chat_id=chat_id, photo=random.choice(error_images), caption="You done reached my daily search limit again :(")

def notFound(query, chat_id):
    return bot.sendPhoto(chat_id=chat_id, photo=random.choice(not_found_images), caption=random.choice(not_found_captions))

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
        return -2


if __name__ == '__main__':
    app.run(debug=True)
