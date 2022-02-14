# -*- encoding: utf8 -*-

import json
import logging
import time
import uuid

import requests

import settings


class TgbotConnection:
    REQUEST_TIMEOUT = settings.REQUEST_TIMEOUT

    def __init__(self, token):
        self.token = token

    def apiurl(self, method):
        return "https://api.telegram.org/bot{}/{}".format(self.token, method)

    def makeRequest(self, reqname, **params):
        response = None
        retries = 0
        while retries <= 3:
            try:
                response = requests.get(
                    self.apiurl(reqname), params=params, timeout=self.REQUEST_TIMEOUT
                )
            except Exception as e:
                logging.exception(
                    f"Exception occurred ({str(e)}) for request: {reqname}, params: {str(params)}, retries: {retries}"
                )
                time.sleep(3)
            else:
                response.encoding = "utf-8"
                break

            retries += 1

        return response

    def sendMessage(self, chat_id, text, **params):
        return self.makeRequest("sendMessage", chat_id=chat_id, text=text, **params)

    def sendPhoto(self, chat_id, photo, caption=None):
        return self.makeRequest(
            "sendPhoto", chat_id=chat_id, photo=photo, caption=caption
        )

    def setWebhook(self, url):
        return self.makeRequest("setWebhook", url=url)

    def sendInlineResponse(self, inline_query_id, items):
        results = []
        for item in items:
            photo_url = item["link"]
            thumb_url = item["image"]["thumbnailLink"]
            results.append(
                InlineQueryResultPhoto(photo_url=photo_url, thumb_url=thumb_url)
            )
        return self.makeRequest(
            "answerInlineQuery",
            inline_query_id=inline_query_id,
            results=json.dumps([ob.__dict__ for ob in results]),
        )


class InlineQueryResultPhoto:
    def __init__(self, photo_url, thumb_url):
        self.type = "photo"
        self.id = str(uuid.uuid4())
        self.photo_url = photo_url
        self.thumb_url = thumb_url
