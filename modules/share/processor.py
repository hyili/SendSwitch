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

    def setTimeout(self, timeout):
        self.timeout = timeout

    def setDescription(self, description):
        self.description = description

    def activate(self):
        self.enable = True

    def deactivate(self):
        self.enable = False

    # customized function here
    def target(self, msg):
        # define your function below
        return msg

    def run(self, msg):
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
class Echo_Processor(Processor):
    def target(self, msg):
        return msg

# Post to Slack Processor Sample
class Post_to_Slack_Processor(Processor):
    def setWebhook(self, webhooks):
        assert isinstance(webhooks, list), "webhooks must be a list."

        self.webhooks = webhooks

    def target(self, msg):
        assert hasattr(self, "webhooks"), "you must setWebhook() first in your client_config.py."

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

