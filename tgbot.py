# -*- encoding: utf8 -*-

import requests
import uuid


class TgbotConnection:
    REQUEST_TIMEOUT = 30
    def __init__(self, token):
        self.token = token

    def apiurl(self, method):
        return 'https://api.telegram.org/bot{}/{}'.format(self.token, method)

    def makeRequest(self, reqname, **params):
        retries = 0
        while True:
            retries += 1
            try:
                response = requests.get(self.apiurl(reqname),
                    params=params, timeout=self.REQUEST_TIMEOUT)
            except requests.exceptions.ConnectionError as ex:
                print('Connection error ({}) for  {} (try #{}), params: {}'.format(
                    ex, reqname, retries, params))
                continue
            except requests.exceptions.Timeout:
                continue
            response.encoding = 'utf-8'
            return response

    def sendMessage(self, chat_id, text):
        return self.makeRequest('sendMessage', chat_id=chat_id, text=text)

    def sendPhoto(self, chat_id, photo, caption=None):
        return self.makeRequest('sendPhoto', chat_id=chat_id, photo=photo, caption=caption)

    def setWebhook(self, url):
        return self.makeRequest('setWebhook', url=url)

    def sendInlineResponse(self, inline_query_id, items):
        results = []
        for item in items:
            photo_url = item["link"]
            thumb_url = item["image"]["thumbnailLink"]
            results.append(InlineQueryResultPhoto(photo_url=photo_url, thumb_url=thumb_url))
        return self.makeRequest('answerInlineQuery', inline_query_id=inline_query_id, results=results)



class InlineQueryResultPhoto:

    def __init__(self, photo_url, thumb_url):
        type = "photo"
        id = uuid.uuid4()
        photo_url = photo_url
        thumb_url = thumb_url
