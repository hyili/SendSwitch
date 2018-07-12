#!/usr/bin/env python3
import pika
import uuid
import time
import datetime
import json
import requests

class Receiver():
    def __init__(self, exchange_id="random", routing_keys=["random"], host="localhost", port=5672, silent_mode=False):
        # rabbitmq host
        self.host = host
        self.port = port
        self.silent_mode = silent_mode

        # exchange_id & routing_keys
        self.exchange_id = exchange_id
        self.routing_keys = routing_keys

        # TODO: result would be lost when restart server
        self.result = dict()

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port))
        self.channel = self.connection.channel()

        # set consume_response to consume the response, and use only once
        self.channel.basic_consume(self.consume_response,
            no_ack=True,
            queue="return")

        self.connection.process_data_events()

    def __del__(self):
        # close connection: after destruction
        try:
            self.channel.stop_consuming()
            self.connection.close()
        except Exception as e:
            pass

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    def reinit(self):
        self.__init__(exchange_id=self.exchange_id,
            routing_keys=self.routing_keys,
            host=self.host,
            port=self.port,
            silent_mode=self.silent_mode
        )

    def consume_response(self, channel, method, properties, body):
        if not self.silent_mode:
            self.Debug("Receive {0}: {1}".format(properties.correlation_id, body.decode("utf-8")))
        self.result.update({properties.correlation_id: body.decode("utf-8")})

    # Non-Blocking
    def check_result(self):
        # dispatch consume_response using process_data_events() until data acquired
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        try:
            self.connection.process_data_events()
        except pika.exceptions.ConnectionClosed:
            try:
                self.reinit()
                self.connection.process_data_events()
            except Exception as e:
                raise Exception("Failed to reconnect. {0}".format(e))
        except Exception as e:
            raise Exception("Error occurred. {0}".format(e))

    def get_current_id(self):
        return self.result.keys()

    # Non-Blocking
    def get_result(self, corr_id):
        ret_val = self.result.pop(corr_id, None)
        return ret_val

    def get(self, corr_id):
        self.check_result()
        return self.get_result(corr_id)

    # for retrying it is not good to push back the result here
    # the rotating time is too short
    def push_back(self, corr_id, result):
        self.result.update({corr_id: result})

    def clear(self):
        self.result.clear()

    def remove(self, corr_id):
        return self.get_result(corr_id)