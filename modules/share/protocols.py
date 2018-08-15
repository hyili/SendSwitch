#!/usr/bin/python3

import time

# Version
class Request():
    def __init__(self, timestamp, expire, data, action, result, reason=None):
        self.request = {
            "created": int(timestamp),
            "expire": expire,
            "data": data,
            "action": {
                "id": action
            },
            "result": {
                "id": result,
                "reason": reason if reason else ""
            }
        }

    def get(self):
        return self.request

# Version
class Response():
    def __init__(self, timestamp, expire, action, result, forward=None, data=None, reason=None):
        self.response = {
            "created": int(timestamp),
            "expire": expire,
            "action": {
                "id": action,
            },
            "result": {
                "id": result,
                "reason": reason if reason else ""
            }
        }

        # Options
        if forward:
            self.response["action"]["forward"] = forward

    def get(self):
        return self.response
