#!/usr/bin/env python3

import requests

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

    def is_active(self):
        return self.enable

    # customized function here
    def target(self, msg):
        # define your function below
        return msg

    def run(self, msg):
        # check if the module is enabled
        if self.is_active():
            self.Debug("{0} is active, Start to process.".format(self.__class__.__name__))
        else:
            self.Debug("{0} is inactive, Skipped.".format(self.__class__.__name__))
            return msg

        # temporarily store msg
        temp_msg = msg

        # run target function
        try:
            # parse to target
            ret = self.target(msg)

            # TODO: check msg structure?
            # if nothing comes back
            if ret is None:
                self.Debug("Nothing returns back, returning the previous result.")
                ret = temp_msg
        except Exception as e:
            ret = temp_msg
            self.Debug("Some error occurred during {0}... Error shows below, Skipped this function".format(self.__class__.__name__))
            self.Debug(e)
        finally:
            return ret

# Echo Processor Sample
class EchoProcessor(Processor):
    def target(self, msg):
        return msg

# Post to Slack Processor Sample
class SlackProcessor(Processor):
    def set_webhook(self, webhooks):
        assert isinstance(webhooks, list), "webhooks must be a list."

        self.webhooks = webhooks

    def target(self, msg):
        assert hasattr(self, "webhooks"), "you must set_webhook() first in your client_config.py."

        data = {
            "text": str("```\n"+str(msg["header"]["subject"])+"\n```")
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
    def set_webhook(self, webhooks):
        assert isinstance(webhooks, list), "webhooks must be a list."

        self.webhooks = webhooks

    def target(self, msg):
        assert hasattr(self, "webhooks"), "you must set_webhook() first in your client_config.py."

        # TODO: defined your own data format
        data = str(msg)

        # post to self-defined outer webhook
        for webhook in self.webhooks:
            r = requests.post(
                webhook,
                json=data
            )

            # TODO: defined your own response handler
            if r.status_code != 200:
                print(r.status_code)
            else:
                print(r.text)

        return msg

# Blacklist/Whitelist sample
class BlacklistWhitelistProcessor(Processor):
    def set_blacklist(self, path):
        # self.blacklist = ["<test@example.com>"]
        self.blacklist = []
        pass
    def set_whitelist(self, path):
        # self.whitelist = ["<test@example.com>"]
        self.whitelist = []
        pass
    def target(self, msg):
        assert hasattr(self, "blacklist"), "you must set_blacklist() first in your client_config.py."
        assert hasattr(self, "whitelist"), "you must set_whitelist() first in your client_config.py."

        # set default action
        msg["result"] = "OK"

        for address in self.whitelist:
            if address in msg["header"]["from"]:
                print("Address in whitelist")
                msg["result"] = "OK"

        for address in self.blacklist:
            if address in msg["header"]["from"]:
                print("Address in blacklist")
                msg["result"] = "Reject"

        return msg
