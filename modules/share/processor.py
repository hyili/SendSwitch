#!/usr/bin/env python3

import subprocess
import base64
import email
import json
import copy
from email.header import decode_header
import requests
import macro

# Processor Template
class Processor():
    def __init__(self, timeout=10, description=None, enable=True, silent_mode=False):
        self.timeout = timeout
        self.description = description
        self.enable = enable
        self.silent_mode = silent_mode

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    def set_timeout(self, timeout):
        self.timeout = timeout

    def set_description(self, description):
        self.description = description

    def activate(self):
        self.enable = True

    def deactivate(self):
        self.enable = False

    def is_activate(self):
        return self.enable

    # customized function here
    def target(self, msg):
        # define your function below
        return msg

    def run(self, msg):
        # check if the module is enabled
        if self.is_activate():
            self.Debug("{0} is active, Start to process.".format(self.__class__.__name__))
        else:
            self.Debug("{0} is inactive, Skipped.".format(self.__class__.__name__))
            return msg

        # Build a new_msg using for customized target
        new_msg = copy.deepcopy(msg)

        # run target function
        try:
            # parse to target
            ret_msg = self.target(new_msg)

            # TODO: check msg structure?
            # if nothing comes back
            if ret_msg is None:
                self.Debug("Nothing returns back, returning the previous arguments.")
                ret_msg = msg
        except Exception as e:
            ret_msg = msg
            self.Debug("Some error occurred during {0}... Error shows below, Skipped this function".format(self.__class__.__name__))
            self.Debug(e)
        finally:
            return ret_msg

# Echo Processor Sample
class EchoProcessor(Processor):
    def target(self, msg):
        print("Echo Here")
        return msg

# Post to Slack Processor Sample
class SlackProcessor(Processor):
    def setWebhooks(self, webhooks):
        assert isinstance(webhooks, list), "webhooks must be a list."

        self.webhooks = webhooks

    def target(self, msg):
        assert hasattr(self, "webhooks"), "you must call setWebhooks() first before calling run()."

        current_msg = msg.getCurrentMsg()
        data = {
            "text": "```\n{0}\n```".format(str(current_msg["header"]["subject"]))
        }

        # post to slack incoming webhook
        for webhook in self.webhooks:
            r = requests.post(
                webhook,
                json=data
            )

            print(r.status_code)
            print(r.text)

        return msg

# Post to Outer Webhook Processor Sample
class WebhookProcessor(Processor):
    def setWebhooks(self, webhooks):
        assert isinstance(webhooks, list), "webhooks must call be a list."

        self.webhooks = webhooks

    def target(self, msg):
        assert hasattr(self, "webhooks"), "you must call setWebhooks() first before calling run()."

        # defined your own data format
        data = str(msg)

        # post to self-defined outer webhook
        for webhook in self.webhooks:
            r = requests.post(
                webhook,
                json=data
            )

            # defined your own response handler
            if r.status_code != 200:
                print(r.status_code)
            else:
                print(r.text)

        return msg

# Blacklist/Whitelist sample
class BlacklistWhitelistProcessor(Processor):
    def setBlacklist(self, path):
        # self.blacklist = ["<test@example.com>"]
        self.blacklist = []
        pass

    def setWhitelist(self, path):
        # self.whitelist = ["<test@example.com>"]
        self.whitelist = []
        pass

    def target(self, msg):
        assert hasattr(self, "blacklist"), "you must call setBlacklist() first before calling run()."
        assert hasattr(self, "whitelist"), "you must call setWhitelist() first before calling run()."

        for address in self.whitelist:
            if address in msg["header"]["from"]:
                print("Address in whitelist")
                msg.setResult(macro.PASS)
                return msg

        for address in self.blacklist:
            if address in msg["header"]["from"]:
                print("Address in blacklist")
                msg.setResult(macro.DENY)
                return msg

        return msg

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
            msg.setCurrentMsg(current_msg)
        except Exception as e:
            return None

        # returning
        return msg

class SpamAssassinProcessor(Processor):
    def extract_result(self, result):
        ED_processor = EmailDecodeProcessor(description="just using for decode spamassassin's result.")
        email = ED_processor.parse_msg_from_bytes(result)
        header = ED_processor.extract_header(email)

        return header

    def target(self, msg):
        process = subprocess.Popen(["spamassassin"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output, error = process.communicate(input=msg.getDecodedMsg())

        header = self.extract_result(output)

        # return result
        try:
            header["x-spam-status"][0].split(",")[0].lower().index("yes")

            print("SPAM found.")
            msg.setResult(macro.SPAM)
        except ValueError:
            print("Not SPAM.")
        finally:
            return msg

class ClamAVProcessor(Processor):
    def extract_result(self, result):
        reports = result.decode().split("\n")
        r = dict()

        for report in reports:
            try:
                temp = report.split("\n")[0].split(":")
                r[temp[0]] = temp[1]
            except:
                continue

        return r

    def target(self, msg):
        process = subprocess.Popen(["clamscan", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output, error = process.communicate(input=msg.getDecodedMsg())

        ret = self.extract_result(output)

        # return result
        try:
            ret["Infected files"].lower().index("1")

            print("VIRUS found.")
            msg.setResult(macro.VIRUS)
        except ValueError:
            print("Not VIRUS.")
        finally:
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
            json_msg = json.dumps(msg.getCurrentMsg())
            self.output.send(json_msg)

        return msg
