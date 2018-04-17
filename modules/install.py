#!/usr/bin/env python3
import pika
import uuid
import sys
import time
import datetime
import json
import requests

class install():
    def __init__(self, username="guest", host="localhost", silent_mode=False):
        # rabbitmq host
        self.host = host
        self.silent_mode = silent_mode

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        self.channel = self.connection.channel()

        # declare exchange
        self.channel.exchange_declare(exchange="random",
            exchange_type="direct",
            passive=False,
            durable=True,
            arguments={
                "alternate-exchange": "dropped"
            }
        )

        self.channel.exchange_declare(exchange="mail",
            exchange_type="direct",
            passive=False,
            durable=True,
            arguments={
                "alternate-exchange": "dropped"
            }
        )

        # DLX
        self.channel.exchange_declare(exchange="return",
            exchange_type="direct",
            passive=False,
            durable=True,
            arguments={
                "alternate-exchange": "dropped"
            }
        )

        # AE
        self.channel.exchange_declare(exchange="dropped",
            exchange_type="topic",
            passive=False,
            durable=True
        )

        # declare queue if there is no current queue exists
        self.channel.queue_declare(queue=username,
            passive=False,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "return",
                "x-dead-letter-routing-key": "return"
            }
        )

        self.channel.queue_declare(queue="return",
            passive=False,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "return",
                "x-dead-letter-routing-key": "return"
            }
        )

        # set queue bindings (can binds many keys to one queue)
        self.channel.queue_bind(exchange="mail",
            queue=username,
            routing_key="mail.{0}@hyili.idv.tw".format(username)
        )

        self.channel.queue_bind(exchange="return",
            queue="return",
            routing_key="return"
        )

        self.channel.queue_bind(exchange="dropped",
            queue="return",
            routing_key="#"
        )

    def __del__(self):
        # close connection: after destruction
        try:
            self.connection.close()
        except:
            pass

if __name__ == "__main__":
    try:
        args = sys.argv
        if len(args) == 2:
            install = install(username=args[1])
        else:
            print("./install.py [username]")
    except KeyboardInterrupt:
        print(" [*] Signal Catched. Quit.")
