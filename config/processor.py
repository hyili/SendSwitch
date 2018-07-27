#!/usr/bin/env python3

import requests
import subprocess

from lib.processor import Processor, EmailDecodeProcessor
import macro

# Echo Processor Sample
class EchoProcessor(Processor):
    def target(self, msg):
        print("Echo Here")
        return msg

# Forward Processor Sample
class ForwardProcessor(Processor):
    def setForwardAddress(self, forward_address):
        assert isinstance(forward_address, str), "forward_address must be a string."

        self.forward_address = forward_address

    def target(self, msg):
        assert hasattr(self, "forward_address"), "you must call setForwardAddress() first before calling run()."

        msg.setAction(macro.ACTION_FORWARD)
        msg.setForward(self.forward_address)

        return msg

# Post to Slack Processor Sample
class SlackProcessor(Processor):
    def setWebhooks(self, webhooks):
        assert isinstance(webhooks, list), "webhooks must be a list."

        self.webhooks = webhooks

    def target(self, msg):
        assert hasattr(self, "webhooks"), "you must call setWebhooks() first before calling run()."

        current_msg = msg.getMsg()
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
                msg.setAction(macro.ACTION_PASS)
                return msg

        for address in self.blacklist:
            if address in msg["header"]["from"]:
                print("Address in blacklist")
                msg.setAction(macro.ACTION_DENY)
                return msg

        return msg

class SpamAssassinProcessor(Processor):
    def extract_result(self, result):
        ED_processor = EmailDecodeProcessor(description="just used for decoding spamassassin's result.")
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
            msg.setResult(macro.TAG_SPAM)
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

        print(msg.getDecodedMsg())

        ret = self.extract_result(output)

        # return result
        try:
            ret["Infected files"].lower().index("1")

            print("VIRUS found.")
            msg.setResult(macro.TAG_VIRUS)
        except ValueError:
            print("Not VIRUS.")
        finally:
            return msg
