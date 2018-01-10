#!/usr/bin/env python3
import pika
import uuid
import sys

class server():
    def __init__(self, exchange_id, routing_keys):
        # corr_id: set for checking if response is for me
        self.corr_id = str(uuid.uuid4())

        # exchange_id & routing_keys
        self.exchange_id = exchange_id
        self.routing_keys = routing_keys

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # declare exchange
        self.channel.exchange_declare(exchange=self.exchange_id, exchange_type="direct")

        # declare response queue
        # callback_queue: a queue for client use
        self.response = self.channel.queue_declare(exclusive=True)
        self.callback_queue_name = self.response.method.queue

        # result: storing result
        self.result = None

    def __del__(self):
        # close connection: after destruction
        self.connection.close()

    def consume_response(self, ch, method, properties, body):
        if self.corr_id == properties.correlation_id:
            print(" [*] Receive %s" % body)
            self.result = body
        else:
            print(" [*] Not mine. Waiting...")

    # Non-Blocking 
    def sendMsg(self, msg):
        # queue publish, send out msg
        for routing_key in self.routing_keys:
            self.channel.basic_publish(exchange=self.exchange_id,
                    routing_key=routing_key,
                    properties=pika.BasicProperties(
                            reply_to=self.callback_queue_name,
                            correlation_id=self.corr_id
                    ),
                    body=msg
            )
            print(" [*] Sent %s to %s" % (msg, routing_key))

        # set consume_response to consume the response
        self.channel.basic_consume(self.consume_response,
                no_ack=True,
                queue=self.callback_queue_name
        )

        self.connection.process_data_events()

    # Non-Blocking 
    def getResult(self):
        # dispatch consume_response using process_data_events() until data acquired
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        # TODO: change here
        self.connection.process_data_events()

        return self.result


# start server
if __name__ == "__main__":
    args = sys.argv
    if len(args) >= 3:
        S = server(exchange_id=args[1], routing_keys=args[2:])
        S.sendMsg("example_message")
        R = None
        # TODO: timeout
        while R is None:
            R = S.getResult()
    else:
        print("./sendmq.py [exchange_id] [routing_key] ...")
