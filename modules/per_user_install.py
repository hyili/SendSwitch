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
        # TODO: Create new vhost
        try:
            r = requests.put("http://localhost:15672/api/vhosts/{0}".format(vhost),
            headers={"Content-Type": "application/json"},
            auth=requests.auth.HTTPBasicAuth(user, password))
            print(r)
        except Exception as e:
            print(e)
            quit()

        # Giving full control to user guest
        try:
            r = requests.put("http://localhost:15672/api/permissions/{0}/guest".format(vhost),
            json={
                "configure": ".*",
                "write": ".*",
                "read": ".*"
            }, auth=requests.auth.HTTPBasicAuth(user, password))
            print(r)
        except Exception as e:
            print(e)
            quit()

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
        try:
            r = requests.put("http://localhost:15672/api/parameters/shovel/%2F/{0}-mail".format(vhost),
            json={
                "component": "shovel",
                "name": "{0}-mail".format(vhost),
                "vhost": "/",
                "value": {
                    "prefetch-count": 1,
                    "reconnect-delay": 5,
                    "ack-mode": "on-confirm",
                    "add-forward-headers": False,
                    "delete-after": "never",
                    "src-uri": "amqp://localhost",
                    "src-queue": vhost,
                    "dest-uri": "amqp://{0}:{1}@localhost/{2}".format(user, password, vhost),
                    "dest-queue": "mail"
                }
            }, auth=requests.auth.HTTPBasicAuth(user, password))
            print(r)
        except Exception as e:
            print(e)
            quit()

        try:
            r = requests.put("http://localhost:15672/api/parameters/shovel/%2F/{0}-return".format(vhost), json={
                "component": "shovel",
                "name": "{0}-return".format(vhost),
                "vhost": "/",
                "value": {
                    "prefetch-count": 1,
                    "reconnect-delay": 5,
                    "ack-mode": "on-confirm",
                    "add-forward-headers": False,
                    "delete-after": "never",
                    "src-uri": "amqp://{0}:{1}@localhost/{2}".format(user, password, vhost),
                    "src-queue": "return",
                    "dest-uri": "amqp://localhost",
                    "dest-queue": "return"
                }
            }, auth=requests.auth.HTTPBasicAuth(user, password))
            print(r)
        except Exception as e:
            print(e)
            quit()

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
