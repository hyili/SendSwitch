#!/usr/bin/env python3

from config_loader import Config
from shared_queue import SharedQueue
from processor import Processor, EchoProcessor, DelayProcessor, SlackProcessor, WebhookProcessor, BlacklistWhitelistProcessor, SpamAssassinProcessor, ClamAVProcessor, ForwardProcessor

##### Create all your processors here #####
processor_1 = EchoProcessor(description="This is echo processor sample.")
processor_2 = DelayProcessor(description="This is delay processor sample.")
processor_2.deactivate()
processor_3 = SlackProcessor(description="This is post to slack processor sample.")
processor_3.setWebhooks(["https://your/slack/webhook/here"])
processor_3.deactivate()
processor_4 = WebhookProcessor(description="This is post to webhook processor sample.")
processor_4.setWebhooks(["https://your/own/webhook/here"])
processor_4.deactivate()
processor_5 = BlacklistWhitelistProcessor(description="This is blacklist & whitelist processor sample.")
processor_5.setBlacklist(addresses=[])
processor_5.setWhitelist(addresses=[])
processor_5.deactivate()
processor_6 = SpamAssassinProcessor(description="This is spamassassin processor sample.")
processor_6.deactivate()
processor_7 = ClamAVProcessor(description="This is clamav processor sample.")
processor_7.deactivate()
processor_8 = ForwardProcessor(description="This is forward processor sample.")
processor_8.setForwardAddress("your@email.here")
processor_8.deactivate()

# Processors
processors = [processor_1, processor_2, processor_3, processor_4, processor_5, processor_6, processor_7, processor_8]

##### Create all your processors above #####

# Output setup
output = SharedQueue()

# Config setup
config = Config(framework_name="framework_name",
    auth={"vhost": "vhost", "user": "user", "password": "password"},
    processors=processors,
    MQ_host="localhost",
    MQ_port=5672,
    web_enable=False,
    web_host="localhost",
    web_port=61666,
    web_secret_key="Th151553cr3tK3y",
    retry_interval=20,
    output=output,
    silent_mode=False
)
