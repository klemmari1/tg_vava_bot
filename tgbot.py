#!/usr/bin/env python3
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
            try:
                json = response.json()
            except TypeError:
                json = response.json
            except ValueError:
                json = response.json
            return json['result']

    def getMe(self):
        return self.makeRequest('getMe')

    def getUpdates(self, offset=None, limit=None, timeout=None):
        updates = self.makeRequest('getUpdates', offset=offset, limit=limit, timeout=timeout)
        if updates is None:
            return []
        return updates

    def sendMessage(self, chat_id, text):
        return self.makeRequest('sendMessage', chat_id=chat_id, text=text)

    def forwardMessage(self, chat_id, from_id, msg_id):
        return self.makeRequest('forwardMessage', chat_id=chat_id,
            from_chat_id=from_id, message_id=msg_id)
