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

        # exchange_id & routing_keys
        self.exchange_id = exchange_id
        self.routing_keys = routing_keys

        # TODO: result would be lost when restart server
        self.result = dict()

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        self.channel = self.connection.channel()

        # set consume_response to consume the response, and use only once
        self.channel.basic_consume(self.consume_response,
            no_ack=True,
            queue="return")

        self.connection.process_data_events()

    # TODO: destructor

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    def consume_response(self, channel, method, properties, body):
        if not self.silent_mode:
            self.Debug("Receive {0}: {1}".format(properties.correlation_id, body.decode("utf-8")))
        self.result.update({properties.correlation_id: body.decode("utf-8")})

    # Non-Blocking
    def checkResult(self):
        # dispatch consume_response using process_data_events() until data acquired
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        try:
            self.connection.process_data_events()
        except pika.exceptions.ConnectionClosed:
            try:
                self.__init__(exchange_id=self.exchange_id,
                    routing_keys=self.routing_keys,
                    host=self.host,
                    silent_mode=self.silent_mode)
                self.connection.process_data_events()
            except Exception as e:
                self.Debug(e)
        except Exception as e:
            self.Debug(e)

    # Non-Blocking
    def getResult(self, corr_id):
        ret_val = self.result.pop(corr_id, None)
        return ret_val

    def get(self, corr_id):
        self.checkResult()
        return self.getResult(corr_id)

    def clear(self):
        self.result.clear()
