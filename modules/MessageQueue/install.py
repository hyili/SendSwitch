#!/usr/bin/env python3

import pika
import uuid
import time
import datetime
import json
import requests

class install():
    def __init__(self, username="guest", email_domain="localhost", host="localhost", port=5672, silent_mode=False):
        # rabbitmq host
        self.host = host
        self.port = port
        self.username = username
        self.email_domain = email_domain
        self.silent_mode = silent_mode

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port))
        self.channel = self.connection.channel()

        # declare exchange
        self.channel.exchange_declare(exchange="mail",
            exchange_type="direct",
            passive=False,
            durable=True,
            arguments={
                "alternate-exchange": "dropped"
            }
        )

        # declare return exchange if there is no current queue exists
        self.channel.exchange_declare(exchange="{0}-return".format(self.username),
            exchange_type="direct",
            passive=False,
            durable=True,
            arguments={
                "alternate-exchange": "dropped"
            }
        )

        # DLX
        self.channel.exchange_declare(exchange="return",
            exchange_type="topic",
            passive=False,
            durable=True
        )

        # AE
        self.channel.exchange_declare(exchange="dropped",
            exchange_type="topic",
            passive=False,
            durable=True
        )

        # declare send queue if there is no current queue exists
        self.channel.queue_declare(queue="{0}-mail".format(self.username),
            passive=False,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "return",
                "x-dead-letter-routing-key": "return"
            }
        )

        self.channel.queue_declare(queue="return",
            passive=False,
            durable=True
        )

        self.channel.queue_declare(queue="dropped",
            passive=False,
            durable=True
        )

        # set send queue bindings (can binds many keys to one queue)
        self.channel.queue_bind(exchange="mail",
            queue="{0}-mail".format(self.username),
            routing_key="mail.{0}@{1}".format(self.username, self.email_domain)
        )

        # set return queue bindings (can binds many keys to one queue)
        self.channel.queue_bind(exchange="{0}-return".format(self.username),
            queue="return",
            routing_key="mail.{0}@{1}".format(self.username, self.email_domain)
        )

        self.channel.queue_bind(exchange="return",
            queue="return",
            routing_key="#"
        )

        self.channel.queue_bind(exchange="dropped",
            queue="dropped",
            routing_key="#"
        )

    def __del__(self):
        # close connection: after destruction
        try:
            self.connection.close()
        except:
            pass
