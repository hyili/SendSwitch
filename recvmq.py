#!/usr/bin/env python3
import pika
import sys
import json
import time
import datetime
import email

class client():
    def __init__(self, exchange_id="random", routing_key="random", host="localhost", silent_mode=False):
        # rabbitmq host
        self.host = host
        self.silent_mode = silent_mode

        # exchange_id & routing_key
        self.exchange_id = exchange_id
        self.routing_key = routing_key

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)

        # declare exchange
        self.channel.exchange_declare(exchange=self.exchange_id,
                exchange_type="direct",
                durable=True)

        # declare request queue where request comes in
        self.request = self.channel.queue_declare(exclusive=True)
        self.request_queue_id = self.request.method.queue

        # set queue bindings (can binds many keys to one queue)
        self.channel.queue_bind(exchange=self.exchange_id,
                queue=self.request_queue_id,
                routing_key=self.routing_key
        )

    def __del__(self):
        # close connection: after destruction
        self.channel.queue_delete(self.request_queue_id)
        self.connection.close()

    def email_handler(self, msg):
        p = email.message_from_string(msg)

        print(" [*] header:")
        for pp_key in set(p.keys()):
            pp_value = p.get_all(pp_key, None)
            if isinstance(pp_value, list):
                for element in pp_value:
                    print(" [-] %s: %s" % (pp_key, element))
            else:
                print(" [-] %s: %s" % (pp_key, pp_value))

        print(" [*] payload:")
        if p.is_multipart():
            for payload in p.get_payload():
                print(" [-] %s" % payload.get_payload())
        else:
            print(" [-] %s" % p.get_payload())


    def consume_request(self, channel, method, properties, body):
        # json format load
        data = json.loads(body)

        # TODO: Message Controller
        if not self.silent_mode:
            print(" [*] Receive %s" % data)

        # email handler
        self.email_handler(data["data"])

        # resoponse message
        msg = "OK"
        timestamp = time.time()
        # message will not actually be removed when times up
        # it will be removed until message head up the limit
        expire = 600 * 1000
        response = {
            "created": int(timestamp),
            "expire": expire,
            "data": msg
        }

        # send response back WITHOUT exchanger
        channel.basic_publish(exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=properties.correlation_id,
                    timestamp=int(timestamp),
                    expiration=str(expire),
                ),
                body=json.dumps(response)
        )
        # TODO: Message Controller
        if not self.silent_mode:
            print(" [*] Sent %s to %s" % (msg, properties.reply_to))

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        # wait for request
        self.channel.basic_consume(self.consume_request,
                exclusive=True,
                queue=self.request_queue_id)

        # dispatch consume_request using start_consuming(), iteratively
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        print(" [*] Waiting for messages. To exit press CTRL+C")
        self.channel.start_consuming()

# start client
if __name__ == "__main__":
    args = sys.argv
    if len(args) == 3:
        C = client(exchange_id=args[1], routing_key=args[2])
        C.run()
    else:
        print("./recvmq.py [exchange_id] [routing_key]")
