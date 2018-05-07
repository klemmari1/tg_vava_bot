# -*- encoding: utf8 -*-

import requests


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

    def sendPhoto(self, chat_id, photo, caption=None):
        return self.makeRequest('sendPhoto', chat_id=chat_id, photo=photo, caption=caption)

    def setWebhook(self, url):
        return self.makeRequest('setWebhook', url=url)
