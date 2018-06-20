#!/usr/bin/env python3

import requests
from config_loader import Config
from shared_queue import Shared_Queue

##### Create all your processors here #####
def echo(msg):
    print("echo here")

    return msg

def post_to_slack(msg):
    print("post to slack here")
    data = {
        "text": str("```\n"+str(msg["header"]["subject"])+"\n```")
    }

    # post to slack incoming webhook
    r = requests.post(
        "{slack_incoming_webhook}",
        json=data
    )

    print(r.status_code)
    print(r.text)

    return msg

def post_to_webhook(msg):
    pass
    # post to outside webhook
    # wait for incoming webhook

# Processors
processors = [echo, post_to_slack]

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
