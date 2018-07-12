#!/usr/bin/env python3

from config_loader import Config
from shared_queue import SharedQueue
from processor import Processor, EchoProcessor, SlackProcessor, WebhookProcessor, BlacklistWhitelistProcessor, SpamAssassinProcessor, ClamAVProcessor

##### Create all your processors here #####
processor_1 = EchoProcessor(description="This is echo processor sample.")
processor_2 = SlackProcessor(description="This is post to slack processor sample.")
processor_2.setWebhook(["https://your/slack/webhook/here"])
processor_2.deactivate()
processor_3 = WebhookProcessor(description="This is post to webhook processor sample.")
processor_3.setWebhook(["https://your/own/webhook/here"])
processor_3.deactivate()
processor_4 = BlacklistWhitelistProcessor(description="This is blacklist & whitelist processor sample.")
processor_4.setBlacklist(path=None)
processor_4.setWhitelist(path=None)
processor_4.deactivate()
processor_5 = SpamAssassinProcessor(description="This is spamassassin processor sample.")
processor_5.deactivate()
processor_6 = ClamAVProcessor(description="This is clamav processor sample.")
processor_6.deactivate()

# Processors
processors = [processor_1, processor_2, processor_3, processor_4, processor_5, processor_6]

##### Create all your processors above #####

# Output setup
output = SharedQueue()

# Config setup
config = Config(auth={"vhost": "vhost", "user": "user", "password": "password"},
    processors=processors,
    MQ_host="localhost",
    MQ_port=5672,
    web_host="localhost",
    web_port=61666,
    retry_interval=20,
    output=output,
    silent_mode=False
)
