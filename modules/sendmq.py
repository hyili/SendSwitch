#!/usr/bin/env python3
import pika
import uuid
import sys
import time
import datetime
import json
import requests

class sender():
    def __init__(self, exchange_id="random", routing_keys=["random"], user_profile=None, host="localhost", silent_mode=False):
        # rabbitmq host
        self.host = host
        self.silent_mode = silent_mode

        # exchange_id & routing_keys
        self.exchange_id = exchange_id
        self.routing_keys = routing_keys

        # user profile
        self.user_profile = user_profile

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
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

    def __del__(self):
        # close connection: after destruction
        try:
            self.connection.close()
        except:
            pass

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
                self.Debug("Sent {0}: {1}".format(corr_id, msg))

    # Non-Blocking
    def sendMsg(self, msg, corr_id=None):
        # queue publish, send out msg
        timestamp = time.time()

        # corr_id: message correlation id
        if corr_id is None:
            corr_id = str(uuid.uuid4())

        # message will not actually be removed when times up
        # it will be removed until message head up the limit
        expire = (600 if self.user_profile is None else self.user_profile.timeout) * 1000
        data = {
            "created": int(timestamp),
            "expire": expire,
            "data": msg,
            "result": "pending"
        }

        try:
            self._sendMsg(timestamp, expire, corr_id, data)
        except pika.exceptions.ConnectionClosed:
            try:
                self.__init__(exchange_id=self.exchange_id,
                    routing_keys=self.routing_keys,
                    host=self.host,
                silent_mode=self.silent_mode)
                self._sendMsg(timestamp, expire, corr_id, data)
            except Exception as e:
                self.Debug(e)
        except Exception as e:
            self.Debug(e)

        return corr_id

# start sender
if __name__ == "__main__":
    args = sys.argv
    try:
        if len(args) == 1:
            r = requests.get("http://{localhost}:60666/routingkey")
            data = r.json()
            S = sender(exchange_id="mail", routing_keys=[data["routing_key"]])
            S.sendMsg("example_message")
        elif len(args) >= 3:
            S = sender(exchange_id=args[1], routing_keys=args[2:])
            S.sendMsg("example_message")
        else:
            print("./sendmq.py [exchange_id] [routing_key] ...")
    except KeyboardInterrupt:
        print(" [*] Signal Catched. Quit.")
    except Exception as e:
        print(e)
        print("./sendmq.py [exchange_id] [routing_key] ...")
