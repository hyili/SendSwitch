#!/usr/bin/env python3
import pika
import sys
import json
import time
import datetime
import email
import requests
from email.header import decode_header

class receiver():
    def __init__(self, exchange_id="random", routing_key="random", host="localhost", silent_mode=False, user="user", password="pass"):
        # credentials
        self.credentials = pika.PlainCredentials(user, password)

        # rabbitmq host
        self.host = host
        self.silent_mode = silent_mode

        # exchange_id & routing_key
        self.exchange_id = exchange_id
        self.routing_key = routing_key

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, virtual_host="/", credentials=self.credentials))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)

        # declare exchange
        self.channel.exchange_declare(exchange=self.exchange_id,
                exchange_type="direct",
                durable=True)

        # declare request queue where request comes in
        self.request = self.channel.queue_declare(queue=self.routing_key)
        self.request_queue_id = self.request.method.queue

        # set queue bindings (can binds many keys to one queue)
        self.channel.queue_bind(exchange=self.exchange_id,
                queue=self.request_queue_id,
                routing_key=self.routing_key
        )

    def __del__(self):
        # close connection: after destruction
        try:
            self.channel.queue_delete(self.request_queue_id)
            self.connection.close()
        except:
            pass

    def extract_payload(self, p):
        for part in p.walk():
            if part.get_content_maintype() == "text":
                charset = part.get_content_charset()
                print(" [-] %s" % part.get_payload(decode=True).decode(charset))
#            if part.get_content_type() == "multipart/alternative":
#                for alter_part in reversed(part.get_payload()):
#                    self.extract_payload(alter_part)

    def email_handler(self, msg):
        p = email.message_from_string(msg)

        print(" [*] header:")
        for pp_key in set(p.keys()):
            pp_value = p.get_all(pp_key, None)
            # TODO: concat 2 header.from into 1
            if isinstance(pp_value, list):
                for element in pp_value:
                    pair = decode_header(element)
                    content = ""
                    for (_content, _charset) in pair:
                        if _charset:
                            content = "%s %s" % (content, _content.decode(_charset))
                        else:
                            if isinstance(_content, (bytes, bytearray)):
                                content = "%s %s" % (content, _content.decode())
                            else:
                                content = "%s %s" % (content, _content)
                    print(" [-] %s:%s" % (pp_key, content))
            else:
                pair = decode_header(pp_value)
                content = ""
                for (_content, _charset) in pair:
                    if _charset:
                        content = "%s %s" % (content, _content.decode(_charset))
                    else:
                        if isinstance(_content, (bytes, bytearray)):
                            content = "%s %s" % (content, _content.decode())
                        else:
                            content = "%s %s" % (content, _content)
                print(" [-] %s:%s" % (pp_key, content))
        print(" [*] payload:")
        self.extract_payload(p)


    def consume_request(self, channel, method, properties, body):
        # json format load
        data = json.loads(body)

        # TODO: Message Controller
        if not self.silent_mode:
            print(" [*] Receive %s" % data)

        # email handler
        try:
            self.email_handler(data["data"])
        except Exception as e:
            print(e)

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
        # wait for request, and do not allow other consumers on current queue
        self.channel.basic_consume(self.consume_request,
                exclusive=True,
                queue=self.request_queue_id)

        # dispatch consume_request using start_consuming(), iteratively
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        print(" [*] Waiting for messages. To exit press CTRL+C")
        self.channel.start_consuming()

# start receiver
if __name__ == "__main__":
    args = sys.argv
    try:
        if len(args) == 3:
            r = requests.get("http://{localhost}:60666/routingkey")
            data = r.json()
            C = receiver(exchange_id="mail", routing_key=data["routing_key"], host="hostname", user=args[1], password=args[2])
            C.run()
        elif len(args) == 5:
            C = receiver(exchange_id=args[1], routing_key=args[2], user=args[3], password=args[4])
            C.run()
        else:
            print("./recvmq.py [exchange_id] [routing_key] [user] [password]")
    except pika.exceptions.ProbableAuthenticationError as e:
        print(e)
    except Exception as e:
        print(e)
        print("./recvmq.py [exchange_id] [routing_key] [user] [password]")
