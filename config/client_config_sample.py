#!/usr/bin/env python3

from config_loader import Config
from shared_queue import SharedQueue
from processor import EchoProcessor

##### Create all your processors here #####
echo_processor = EchoProcessor(description="This is echo processor sample.")

# Processors
processors = [echo_processor]

##### Create all your processors above #####

# Output setup
output = SharedQueue()

# Config setup
config = Config(framework_name="framework_name",
    auth={"vhost": "test", "user": "test", "password": "test"},
    processors=processors,
    MQ_host="localhost",
    MQ_port=5672,
    web_host="localhost",
    web_port=61666,
    web_secret_key="Th151553cr3tK3y",
    retry_interval=20,
    output=output,
    silent_mode=False
)
