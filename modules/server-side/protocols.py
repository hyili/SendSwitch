#!/usr/bin/python3

import time

class Request():
    def __init__(self, timestamp, expire, data, result):
        self.request = {
            "created": int(timestamp),
            "expire": expire,
            "data": data,
            "result": result
        }

    def get(self):
        return self.request
