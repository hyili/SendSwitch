#!/usr/bin/env python3

import sys
import requests

sys.path.append("../modules/share")
from config_loader import Config
from shared_queue import Shared_Queue
from processor import Processor, Echo_Processor, Post_to_Slack_Processor, Post_to_Webhook_Processor, Blacklist_Whitelist_Processor

##### Create all your processors here #####
processor_1 = Echo_Processor(description="This is echo processor sample.")
processor_2 = Post_to_Slack_Processor(description="This is post to slack processor sample.")
processor_2.setWebhook(["slack_webhook_list"])
processor_3 = Post_to_Webhook_Processor(description="This is post to webhook processor sample.")
processor_3.setWebhook(["https://your/own/webhook/here"])
processor_3.deactivate()
processor_4 = Blacklist_Whitelist_Processor(description="This is blacklist & whitelist processor sample.")
processor_4.setBlacklist(path=None)
processor_4.setWhitelist(path=None)

# Processors
processors = [processor_1, processor_2, processor_3, processor_4]

##### Create all your processors above #####

# Output setup
output = Shared_Queue()

# Config setup
config = Config(auth={"vhost": "vhost", "user": "user", "password": "password"},
    processors=processors,
    MQ_host="localhost",
    MQ_port=5672,
    web_host="localhost",
    web_port=61666,
    output=output)
