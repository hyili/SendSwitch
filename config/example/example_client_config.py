#!/usr/bin/env python3

import sys
import requests

sys.path.append("../modules/share")
from config_loader import Config
from shared_queue import Shared_Queue
from processor import Processor, Echo_Processor, Post_to_Slack_Processor

##### Create all your processors here #####
processor_1 = Echo_Processor(description="This is echo processor sample.")
processor_2 = Post_to_Slack_Processor(description="This is post to slack processor sample.")
processor_2.setWebhook(["slack_webhook_list"])

# Processors
processors = [processor_1, processor_2]

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
