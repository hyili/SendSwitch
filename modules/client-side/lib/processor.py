#!/usr/bin/env python3

import base64
import email
import json
import copy
from email.header import decode_header

# Processor Template
class Processor():
    def __init__(self, timeout=10, description=None, enable=True, silent_mode=False):
        self.timeout = timeout
        self.description = description
        self.enable = enable
        self.silent_mode = silent_mode
        self.terminated = False

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    def setTimeout(self, timeout):
        self.timeout = timeout

    def setDescription(self, description):
        self.description = description

    def activate(self):
        self.enable = True

    def deactivate(self):
        self.enable = False

    def isActivate(self):
        return self.enable

    def terminate(self):
        self.terminated = True
        exit()

    def isTerminated(self):
        return self.terminated

    # customized function here
    def target(self, msg):
        # define your function below
        return msg

    def run(self, msg):
        # check if the module is enabled
        if self.isActivate():
            self.Debug("{0} is active, Start to process.".format(self.__class__.__name__))
        else:
            self.Debug("{0} is inactive, Skipped.".format(self.__class__.__name__))
            return msg, self.isTerminated()

        # Build a new_msg using for customized target
        new_msg = copy.deepcopy(msg)
        ret_msg = msg

        # run target function
        try:
            # parse to target
            ret_msg = self.target(new_msg)

            # TODO: check msg structure?
            # if nothing comes back
            if ret_msg is None:
                self.Debug("Nothing returns back, returning the previous arguments.")
        except Exception as e:
            self.Debug("Some error occurred during {0}... Error shows below, Skipped this function".format(self.__class__.__name__))
            self.Debug(e)
        finally:
            return ret_msg, self.isTerminated()

# Email Encoder/Decoder
class EmailDecodeProcessor(Processor):
    def parse_msg_from_bytes(self, msg):
        return email.message_from_bytes(msg)

    def extract_header(self, p):
        ret = dict()
        for key in set(p.keys()):
            # get all the headers which named key
            value = p.get_all(key, None)
            # init header part
            ret[key.lower()] = list()
            for element in value:
                pair = decode_header(element)
                content = ""
                for (_content, _charset) in pair:
                    try:
                        if _charset:
                            content = "{0} {1}".format(content, _content.decode(_charset))
                        else:
                            if isinstance(_content, (bytes, bytearray)):
                                content = "{0} {1}".format(content, _content.decode())
                            else:
                                content = "{0} {1}".format(content, _content)
                    except:
                        if isinstance(_content, (bytes, bytearray)):
                            content = "{0} {1}".format(content, _content.decode())
                        else:
                            content = "{0} {1}".format(content, _content)

                ret[key.lower()].insert(0, content)

        return ret

    def extract_payload(self, p):
        ret = ""
        # TODO: Can extend more content type here
        for part in p.walk():
            if part.get_content_maintype() == "text":
                charset = part.get_content_charset()
                try:
                    if charset:
                        payload = part.get_payload(decode=True).decode(charset, errors="replace")
                        ret += payload
                    else:
                        payload = part.get_payload(decode=True).decode(errors="replace")
                        ret += payload
                except:
                    payload = part.get_payload(decode=True).decode(errors="replace")
                    ret += payload

        return ret

    def target(self, msg):
        current_msg = dict()

        try:
            # Decode the msg
            decoded_msg = base64.b64decode(msg.getOriginMsg().encode())

            # Decode the email
            human_readable_msg = self.parse_msg_from_bytes(decoded_msg)

            # Extracting header
            current_msg["header"] = self.extract_header(human_readable_msg)

            # Extracting payload
            current_msg["payload"] = self.extract_payload(human_readable_msg)

            # store the result into msg
            msg.setDecodedMsg(decoded_msg)
            msg.setMsg(current_msg)
        except Exception as e:
            return None

        # returning
        return msg

class RedirectOutputProcessor(Processor):
    def setOutput(self, output):
        # TODO: check self.output type
        # set output Shared_Queue
        self.output = output

    # redirect to web output
    def target(self, msg):
        assert hasattr(self, "output"), "you must call setOutput() first before calling run()."

        if self.output is not None:
            json_msg = json.dumps(msg.getMsg())
            self.output.send(json_msg)

        return msg
