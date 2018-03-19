#!/usr/bin/env python3
import pika
import uuid
import sys
import time
import datetime
import json
import requests

class per_user_install():
    def __init__(self, host="localhost", silent_mode=False, vhost="/", user="guest", password="guest"):
        # credentials
        self.credentials = pika.PlainCredentials(user, password)

        # rabbitmq host
        self.host = host
        self.silent_mode = silent_mode

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, virtual_host=vhost, credentials=self.credentials))
        self.channel = self.connection.channel()

        # declare queue if there is no current queue exists
        self.channel.queue_declare(queue="mail",
                                   passive=False,
                                   durable=True)

        self.channel.queue_declare(queue="return",
                                   passive=False,
                                   durable=True)

        # TODO: install shovel

    def __del__(self):
        # close connection: after destruction
        try:
            self.connection.close()
        except:
            pass

if __name__ == "__main__":
    args = sys.argv
    if len(args) == 2:
        install = per_user_install(vhost=args[1])
    else:
        print("./per_user_install.py [username]")
