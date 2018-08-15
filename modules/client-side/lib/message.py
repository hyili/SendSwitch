#!/usr/bin/env python3

import macro

class Message():
    def __init__(self, origin_msg, origin_action=macro.ACTION_DEFAULT, origin_result=macro.TAG_NOTHING):
        self.origin_msg = origin_msg
        self.origin_action = origin_action
        self.origin_result = origin_result

        self.decoded_msg = None

        self.current_action = origin_action
        self.current_result = origin_result
        self.current_msg = None

        self.forward_address = None
        self.reason = None

    def setDecodedMsg(self, decoded_msg):
        self.decoded_msg = decoded_msg

    # get email message from bytes
    def getDecodedMsg(self):
        return self.decoded_msg

    # get base64 encoded message
    def getOriginMsg(self):
        return self.origin_msg

    def setMsg(self, msg):
        self.current_msg = msg

    # get structured message
    def getMsg(self):
        return self.current_msg

    def setResult(self, result):
        self.current_result = result

    def getResult(self):
        return self.current_result

    def setAction(self, action):
        self.current_action = action

    def getAction(self):
        return self.current_action

    def setForward(self, forward):
        self.forward_address = forward

    def getForward(self):
        return self.forward_address

    def setReason(self, reason):
        self.reason = reason

    def getReason(self):
        return self.reason
