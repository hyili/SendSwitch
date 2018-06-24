#!/usr/bin/env python3
import pika
import uuid
import sys
import time
import datetime
import json
import requests

from protocols import Request

class sender():
    def __init__(self, timeout=600, exchange_id="random", routing_keys=["random"], user_profile=None, host="localhost", port=5672, silent_mode=False):
        # rabbitmq host
        self.host = host
        self.port = port
        self.silent_mode = silent_mode

        # exchange_id & routing_keys
        self.exchange_id = exchange_id
        self.routing_keys = routing_keys

        # user profile
        self.user_profile = user_profile

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port))
        self.channel = self.connection.channel()

        # declare response queue
        # callback_queue: a queue for receiver to write, and can only read
        # using current connection
        self.response = self.channel.queue_declare(queue="return",
            durable=True,
            arguments={
                "x-dead-letter-exchange": "return",
                "x-dead-letter-routing-key": "return"
            }
        )
        self.response_queue_id = self.response.method.queue

        # set queue bindings (can binds many keys to one queue)
        self.channel.queue_bind(exchange="return",
            queue=self.response_queue_id,
            routing_key=self.response_queue_id
        )

        # result: storing result
        self.result = []

        self.timeout = 600

    def __del__(self):
        # close connection: after destruction
        try:
            self.connection.close()
        except Exception as e:
            self.Debug(e)

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    def _sendMsg(self, timestamp, expire, corr_id, data):
        for routing_key in self.routing_keys:
            msg = json.dumps(data)
            self.channel.basic_publish(exchange=self.exchange_id,
                routing_key=routing_key,
                properties=pika.BasicProperties(
                    reply_to=self.response_queue_id,
                    correlation_id=corr_id,
                    timestamp=int(timestamp),
                    expiration=str(expire)
                ),
                body=msg
            )

            # Message Controller
            if not self.silent_mode:
                self.Debug("Sent {0}: {1}".format(corr_id, request.get()))

    # Non-Blocking
    def sendMsg(self, msg, corr_id=None, result="Pending"):
        # corr_id: message correlation id
        if corr_id is None:
            corr_id = str(uuid.uuid4())

        # queue publish, send out msg
        timestamp = time.time()
        # message will not actually be removed when times up
        # it will be removed until message head up the limit
        expire = (self.timeout if self.user_profile is None else self.user_profile.timeout) * 1000
        request = Request(timestamp=timestamp, expire=expire,
            data=msg, result=result)

        try:
            self._sendMsg(timestamp, expire, corr_id, request.get())
        except pika.exceptions.ConnectionClosed:
            try:
                self.__init__(exchange_id=self.exchange_id,
                    routing_keys=self.routing_keys,
                    host=self.host,
                silent_mode=self.silent_mode)
                self._sendMsg(timestamp, expire, corr_id, request.get())
            except Exception as e:
                self.Debug(e)
        except Exception as e:
            self.Debug(e)

        return corr_id
