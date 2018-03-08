#!/usr/bin/env python3
import pika
import uuid
import sys
import time
import datetime
import json
import requests

class sender():
    def __init__(self, exchange_id="random", routing_keys=["random"], host="localhost", silent_mode=False):
        # rabbitmq host
        self.host = host
        self.silent_mode = silent_mode

        # corr_id: set for checking if response is for me
        self.corr_id = str(uuid.uuid4())

        # exchange_id & routing_keys
        self.exchange_id = exchange_id
        self.routing_keys = routing_keys

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        self.channel = self.connection.channel()

        # declare exchange
        self.channel.exchange_declare(exchange=self.exchange_id,
                exchange_type="direct",
                durable=True)

        # declare request queue if there is no current queue exists
        # because an exchange won't store any messages, but a queue
        for routing_key in self.routing_keys:
            request = self.channel.queue_declare(queue=routing_key)
            request_queue_id = request.method.queue

            # set queue bindings (can binds many keys to one queue)
            self.channel.queue_bind(exchange=self.exchange_id,
                    queue=request_queue_id,
                    routing_key=routing_key
            )

        # declare response queue
        # callback_queue: a queue for receiver to write, and can only read
        # using current connection
        self.response = self.channel.queue_declare(exclusive=True)
        self.response_queue_id = self.response.method.queue

        # result: storing result
        self.result = []

    def __del__(self):
        # close connection: after destruction
        try:
#           self.channel.exchange_delete(exchange=self.exchange_id)
            self.channel.queue_delete(queue=self.response_queue_id)
            self.connection.close()
        except:
            pass

    def consume_response(self, ch, method, properties, body):
        if self.corr_id == properties.correlation_id:
            # TODO: Message Controller
            if not self.silent_mode:
                print(" [*] Receive %s" % body)
            self.result.append(body)
        else:
            # TODO: Message Controller
            if not self.silent_mode:
                print(" [*] Not mine. Waiting...")

    # Non-Blocking
    def sendMsg(self, msg):
        # queue publish, send out msg
        timestamp = time.time()
        # message will not actually be removed when times up
        # it will be removed until message head up the limit
        expire = 600 * 1000
        data = {
            "created": int(timestamp),
            "expire": expire,
            "data": msg
        }
        for routing_key in self.routing_keys:
            self.channel.basic_publish(exchange=self.exchange_id,
                    routing_key=routing_key,
                    properties=pika.BasicProperties(
                            reply_to=self.response_queue_id,
                            correlation_id=self.corr_id,
                            timestamp=int(timestamp),
                            expiration=str(expire)
                    ),
                    body=json.dumps(data)
            )
            # TODO: Message Controller
            if not self.silent_mode:
                print(" [*] Sent %s to %s" % (msg, routing_key))

        # set consume_response to consume the response, and use only once(FCFS)
        self.channel.basic_consume(self.consume_response,
                no_ack=True,
                exclusive=True,
                queue=self.response_queue_id
        )

        self.connection.process_data_events()

    # Non-Blocking
    def getResult(self):
        # dispatch consume_response using process_data_events() until data acquired
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        # TODO: change here
        self.connection.process_data_events()

        return self.result


# start sender
if __name__ == "__main__":
    args = sys.argv
    try:
        if len(args) == 1:
            r = requests.get("http://{localhost}:60666/routingkey")
            data = r.json()
            S = sender(exchange_id="mail", routing_keys=[data["routing_key"]])
            S.sendMsg("example_message")
            R = S.getResult()
            # TODO: timeout
            while len(R) == 0:
                R = S.getResult()
        elif len(args) >= 3:
            S = sender(exchange_id=args[1], routing_keys=args[2:])
            S.sendMsg("example_message")
            R = S.getResult()
            # TODO: timeout
            while len(R) != len(args) - 2:
                R = S.getResult()
        else:
            print("./sendmq.py [exchange_id] [routing_key] ...")
    except Exception as e:
        print("./sendmq.py [exchange_id] [routing_key] ...")
