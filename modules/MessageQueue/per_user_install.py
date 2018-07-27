#!/usr/bin/env python3

import pika
import uuid
import time
import datetime
import json
import requests

class per_user_install():
    def __init__(self, username="guest", email_domain="localhost", host="localhost", port=5672, web_port=15672, silent_mode=False,
        vhost="/", admin_user="guest", admin_password="guest"):

        # rabbitmq host
        self.host = host
        self.port = port
        self.username = username
        self.email_domain = email_domain
        self.web_port = web_port
        self.vhost = vhost
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.silent_mode = silent_mode

        # Create new vhost
        try:
            r = requests.put("http://{0}:{1}/api/vhosts/{2}".format(self.host, self.web_port, self.vhost),
            headers={"Content-Type": "application/json"},
            auth=requests.auth.HTTPBasicAuth(self.admin_user, self.admin_password))
            self.Debug(r)
        except Exception as e:
            self.Debug(e)
            quit()

        # Giving full control to user guest
        try:
            r = requests.put("http://{0}:{1}/api/permissions/{2}/guest".format(self.host, self.web_port, self.vhost),
            json={
                "configure": ".*",
                "write": ".*",
                "read": ".*"
            }, auth=requests.auth.HTTPBasicAuth(self.admin_user, self.admin_password))
            self.Debug(r)
        except Exception as e:
            self.Debug(e)
            quit()

        # credentials
        self.credentials = pika.PlainCredentials(self.admin_user, self.admin_password)

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port, virtual_host=self.vhost, credentials=self.credentials))
        self.channel = self.connection.channel()

        # DLX & AE
        self.channel.exchange_declare(exchange="return",
            exchange_type="topic",
            passive=False,
            durable=True
        )

        self.channel.exchange_declare(exchange="mail",
            exchange_type="direct",
            passive=False,
            durable=True,
            arguments={
                "alternate-exchange": "return"
            }
        )

        self.channel.queue_declare(queue="return",
            passive=False,
            durable=True
        )

        # declare queue if there is no current queue exists
        self.channel.queue_declare(queue="mail",
            passive=False,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "return",
                "x-dead-letter-routing-key": "return"
            }
        )

        self.channel.queue_bind(exchange="return",
            queue="return",
            routing_key="#"
        )

        self.channel.queue_bind(exchange="mail",
            queue="mail",
            routing_key="mail.{0}@{1}".format(self.username, self.email_domain)
        )

        time.sleep(5)

        # install shovel
        try:
            r = requests.put("http://{0}:{1}/api/parameters/shovel/%2F/{2}-mail".format(self.host, self.web_port, self.vhost),
            json={
                "component": "shovel",
                "name": "{0}-mail".format(self.vhost),
                "vhost": "/",
                "value": {
                    "prefetch-count": 1,
                    "reconnect-delay": 5,
                    "ack-mode": "on-confirm",
                    "add-forward-headers": False,
                    "delete-after": "never",
                    "src-uri": "amqp://localhost",
                    "src-queue": "{0}-mail".format(self.vhost),
                    "dest-uri": "amqp://{0}:{1}@localhost/{2}".format(self.admin_user, self.admin_password, self.vhost),
                    "dest-exchange": "mail",
                    "dest-exchange-key": "mail.{0}@{1}".format(self.username, self.email_domain)
                }
            }, auth=requests.auth.HTTPBasicAuth(admin_user, admin_password))
            self.Debug(r)
        except Exception as e:
            self.Debug(e)
            quit()

        try:
            r = requests.put("http://{0}:{1}/api/parameters/shovel/%2F/{2}-return".format(self.host, self.web_port, self.vhost), json={
                "component": "shovel",
                "name": "{0}-return".format(self.vhost),
                "vhost": "/",
                "value": {
                    "prefetch-count": 1,
                    "reconnect-delay": 5,
                    "ack-mode": "on-confirm",
                    "add-forward-headers": False,
                    "delete-after": "never",
                    "src-uri": "amqp://{0}:{1}@localhost/{2}".format(self.admin_user, self.admin_password, self.vhost),
                    "src-queue": "return",
                    "dest-uri": "amqp://localhost",
                    "dest-exchange": "{0}-return".format(self.vhost)
                }
            }, auth=requests.auth.HTTPBasicAuth(admin_user, admin_password))
            self.Debug(r)
        except Exception as e:
            self.Debug(e)
            quit()

    def __del__(self):
        # close connection: after destruction
        try:
            self.connection.close()
        except:
            pass

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))
