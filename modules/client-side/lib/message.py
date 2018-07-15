#!/usr/bin/env python3

import macro

class Message():
    def __init__(self, origin_msg, origin_result=macro.PASS):
        self.origin_msg = origin_msg
        self.origin_result = origin_result
        self.decoded_msg = None
        self.current_result = origin_result
        self.current_msg = None

    def setDecodedMsg(self, decoded_msg):
        self.decoded_msg = decoded_msg

    def getDecodedMsg(self):
        return self.decoded_msg

    def getOriginMsg(self):
        return self.origin_msg

    def setCurrentMsg(self, msg):
        self.current_msg = msg

    def getCurrentMsg(self):
        return self.current_msg

    def setResult(self, result):
        self.current_result = result

    def getResult(self):
        return self.current_result
