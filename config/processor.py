#!/usr/bin/env python3

import re
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

        # fetch subject and part of payload
        current_msg = msg.getMsg()
        subject = str(current_msg["header"]["subject"][0])
        if len(current_msg["payload"]) > 100:
            payload = "{0} ...".format(str(current_msg["payload"][0:100]))
        else:
            payload = str(current_msg["payload"])

        # construct according to slack webhook format
        data = {
            "text": "```\nSubject:\n{0}\nContent:\n{1}```".format(subject, payload)
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
        assert isinstance(webhooks, list), "webhooks must be a list."

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
    def setBlacklist(self, addresses):
        assert isinstance(addresses, list), "address must be a list."

        self.blacklist = addresses

    def setWhitelist(self, addresses):
        assert isinstance(addresses, list), "address must be a list."

        self.whitelist = addresses

    def target(self, msg):
        blacklist_enable = hasattr(self, "blacklist")
        whitelist_enable = hasattr(self, "whitelist")
        assert blacklist_enable or whitelist_enable, "you must call setBlacklist() or setWhitelist() first before calling run()."

        # https://tools.ietf.org/html/rfc5322#section-3.6.2
        FROM_ADDR = re.compile(r"(.*) (<)?(.*)(>)?", re.IGNORECASE)
        from_addr = re.sub(FROM_ADDR, r"\3", msg.getMsg()["header"]["from"][0], count=1)

        if whitelist_enable:
            for address in self.whitelist:
                if address == from_addr:
                    print("Address in whitelist")
                    msg.setAction(macro.ACTION_PASS)
                    return msg

        if blacklist_enable:
            for address in self.blacklist:
                if address == from_addr:
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

class DelayProcessor(Processor):
    def target(self, msg):
        msg.setAction(macro.ACTION_DELAY)
        msg.setReason("wait for a while")
        self.terminate()

        return msg

class VotingProcessor(Processor):
    def setCandidate(self, name):
        if not hasattr(self, "candidates"):
            self.candidates = dict()
        if not hasattr(self, "voters"):
            self.voters = dict()

        print("Add \"{0}\" to candidate".format(name))
        self.candidates[name] = 0
        self.voters[name] = list()

    def setAPI(self, api, api_key):
        self.api = api
        self.api_key = api_key

    def setSender(self, sender)
        self.sender = sender

    def vote(self, who, what):
        if what in self.candidates:
            if who not in self.voters[what]:
                self.candidates[what] += 1
                self.voters[what].append(who)
                return "OK, vote for \"{0}\"".format(what)
            return "Repeat voting is not allowed"
        return "No such candidate \"{0}\"".format(what)

    def result(self, who, result):
        data = {
            "api_key": self.api_key,
            "data": {
                "mail_from": self.sender,
                "mail_to": [who],
                "cc_to": [],
                "bcc_to": [],
                "subject": "[Vote] Result",
                "content": result
            }
        }

        r = requests.post(
            self.api,
            json=data
        )

        print(r.status_code)
        print(r.text)


    def target(self, msg):
        assert hasattr(self, "candidates") and hasattr(self, "voters"), "you must call setCandidate() first before calling run()."
        assert hasattr(self, "api") and hasattr(self, "api_key"), "you must call setAPI() first before calling run()."
        assert hasattr(self, "sender"), "you must call setSender() first before calling run()."

        # https://tools.ietf.org/html/rfc5322#section-3.6.2
        subject_format = re.compile(r"-<-VOTE->-", re.IGNORECASE)
        sender_format = re.compile(r"(.*) (<)?(.*)(>)?", re.IGNORECASE)
        candidate_format = re.compile(r"(.*)-<-(.*)->-(.*)", re.DOTALL)

        current_msg = msg.getMsg()
        subject = re.search(subject_format, current_msg["header"]["subject"][0])
        if subject is None:
            print("not voting email")
            return msg

        sender = re.sub(sender_format, r"\3", current_msg["header"]["from"][0])
        candidate = re.sub(candidate_format, r"\2", current_msg["payload"])

        ret_msg = self.vote(sender, candidate)
        self.result(sender, ret_msg)

        print(self.candidates)

        return msg
