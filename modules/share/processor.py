#!/usr/bin/env python3

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

    def is_active(self):
        return self.enable

    # customized function here
    def target(self, msg, pre_result):
        # define your function below
        result = pre_result

        return msg, result

    def run(self, msg, pre_result):
        # check if the module is enabled
        if self.is_active():
            self.Debug("{0} is active, Start to process.".format(self.__class__.__name__))
        else:
            self.Debug("{0} is inactive, Skipped.".format(self.__class__.__name__))
            return msg, pre_result

        # temporarily store
        temp_msg = msg
        temp_result = pre_result

        # run target function
        try:
            # parse to target
            ret_msg, ret_result = self.target(msg, pre_result)

            # TODO: check msg structure?
            # if nothing comes back
            if ret_msg is None or ret_result is None:
                self.Debug("Nothing returns back, returning the previous arguments.")
                ret_msg = temp_msg
                ret_result = temp_result
        except Exception as e:
            ret_msg = temp_msg
            ret_result = temp_result
            self.Debug("Some error occurred during {0}... Error shows below, Skipped this function".format(self.__class__.__name__))
            self.Debug(e)
        finally:
            return ret_msg, ret_result

# Echo Processor Sample
class EchoProcessor(Processor):
    def target(self, msg, pre_result):
        return msg, pre_result

# Post to Slack Processor Sample
class SlackProcessor(Processor):
    def set_webhook(self, webhooks):
        assert isinstance(webhooks, list), "webhooks must be a list."

        self.webhooks = webhooks

    def target(self, msg, pre_result):
        assert hasattr(self, "webhooks"), "you must set_webhook() first in your client_config.py."

        result = pre_result

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

        return msg, result

# Post to Outer Webhook Processor Sample
class WebhookProcessor(Processor):
    def set_webhook(self, webhooks):
        assert isinstance(webhooks, list), "webhooks must be a list."

        self.webhooks = webhooks

    def target(self, msg, pre_result):
        assert hasattr(self, "webhooks"), "you must set_webhook() first in your client_config.py."

        result = pre_result

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

        return msg, result

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
    def target(self, msg, pre_result):
        assert hasattr(self, "blacklist"), "you must set_blacklist() first in your client_config.py."
        assert hasattr(self, "whitelist"), "you must set_whitelist() first in your client_config.py."

        # set default action
        result = pre_result

        for address in self.whitelist:
            if address in msg["header"]["from"]:
                print("Address in whitelist")
                result = macro.PASS
                return msg, result

        for address in self.blacklist:
            if address in msg["header"]["from"]:
                print("Address in blacklist")
                result = macro.DENY
                return msg, result

        return msg, result
