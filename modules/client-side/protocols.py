#!/usr/bin/python3

import time

# TODO: Add protocol version
# TODO: Combine client & server protocol
class Response():
    def __init__(self, timestamp, expire, result, data=None, reason=None):
        self.response = {
            "created": int(timestamp),
            "expire": expire,
            "result": result
        }

    def get(self):
        return self.response
