#!/usr/bin/env python3
# -*- encoding: utf8 -*-

import os
import tgbot
import urllib.request
import json


class GoogleImageBot:
    def __init__(self, connection):
        self.conn = connection
        self.update_offset = 0
        self.running = False
        me = self.conn.getMe()
        self.username = me['username']

    def run(self):
        self.running = True
        self.loopUpdates()

    def loopUpdates(self):
        while self.running:
            for update in self.conn.getUpdates(
                    offset=self.update_offset, timeout=60):
                self.handleUpdate(update)

    def get_image_url(self, search_term):
        try:
            key = open("g_key.txt").read().strip()
            cx = open("g_cx.txt").read().strip()
            searchType = "image"
            search_term = search_term.replace(" ", "+")
            url = "https://www.googleapis.com/customsearch/v1?q=" + search_term + "&key=" + key + "&cx=" + cx + "&searchType=" + searchType
            contents = urllib.request.urlopen(url).read()
            j = json.loads(contents)
            return j["items"][0]["link"]
        except Exception as e:
            print("Exception: " + str(e))

    def cmdImg(self, text, chat):
        self.conn.sendMessage(chat['id'], self.get_image_url(text))

    def handleUpdate(self, update):
        upid = update['update_id']
        try:
            msg = update['message']
        except Exception as e:
            print("Exception: " + e)
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


def main():
    token = open("token.txt").read().strip()
    bot = GoogleImageBot(tgbot.TgbotConnection(token))
    print(bot.conn.getMe())
    bot.run()

if __name__ == '__main__':
    main()
