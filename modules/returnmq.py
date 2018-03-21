#!/usr/bin/env python3
import pika
import uuid
import sys
import time
import datetime
import json
import requests

class result_handler():
    def __init__(self, exchange_id="random", routing_keys=["random"], host="localhost", silent_mode=False):
        # rabbitmq host
        self.host = host
        self.silent_mode = silent_mode

        # result
        self.result = dict()

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        self.channel = self.connection.channel()

        # set consume_response to consume the response, and use only once(FCFS)
        self.channel.basic_consume(self.consume_response,
                no_ack=True,
                queue="return"
        )

        self.connection.process_data_events()

    def consume_response(self, ch, method, properties, body):
        # TODO: Message Controller
        if not self.silent_mode:
            print(" [*] Receive %s: %s" % (properties.correlation_id, body))
            self.result.update({properties.correlation_id: body})

    # Non-Blocking
    def checkResult(self):
        # dispatch consume_response using process_data_events() until data acquired
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        try:
            self.connection.process_data_events()
        except Exception as e:
            print(e)

    # Non-Blocking
    def getResult(self, corr_id):
        try:
            ret_val = self.result[corr_id]
            del self.result[corr_id]
            return ret_val
        except:
            return None

    def get(self, corr_id):
        self.checkResult()
        return self.getResult(corr_id)
