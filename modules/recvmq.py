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
    def __init__(self, exchange_id="random", routing_key="random", host="localhost", silent_mode=False, vhost="/", user="guest", password="guest"):
        # credentials
        self.credentials = pika.PlainCredentials(user, password)

        # rabbitmq host
        self.host = host
        self.silent_mode = silent_mode

        # exchange_id & routing_key
        self.exchange_id = exchange_id
        self.routing_key = routing_key

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, virtual_host=vhost, credentials=self.credentials))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)

        # declare request queue where request comes in
        self.request = self.channel.queue_declare(queue="mail",
                                                  passive=True)
        self.request_queue_id = self.request.method.queue

    def __del__(self):
        # close connection: after destruction
        try:
            self.connection.close()
        except:
            pass

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    def extract_payload(self, p):
        for part in p.walk():
            if part.get_content_maintype() == "text":
                charset = part.get_content_charset()
                self.Debug(part.get_payload(decode=True).decode(charset))
#            if part.get_content_type() == "multipart/alternative":
#                for alter_part in reversed(part.get_payload()):
#                    self.extract_payload(alter_part)

    def email_handler(self, msg):
        p = email.message_from_string(msg)

        self.Debug("header:")
        for pp_key in set(p.keys()):
            pp_value = p.get_all(pp_key, None)
            # TODO: concat 2 header.from into 1
            if isinstance(pp_value, list):
                for element in pp_value:
                    pair = decode_header(element)
                    content = ""
                    for (_content, _charset) in pair:
                        if _charset:
                            content = "{0} {1}".format(content, _content.decode(_charset))
                        else:
                            if isinstance(_content, (bytes, bytearray)):
                                content = "{0} {1}".format(content, _content.decode())
                            else:
                                content = "{0} {1}".format(content, _content)
                    self.Debug("{0}:{1}".format(pp_key, content))
            else:
                pair = decode_header(pp_value)
                content = ""
                for (_content, _charset) in pair:
                    if _charset:
                        content = "{0} {1}".format(content, _content.decode(_charset))
                    else:
                        if isinstance(_content, (bytes, bytearray)):
                            content = "{0} {1}".format(content, _content.decode())
                        else:
                            content = "{0} {1}".format(content, _content)
                self.Debug("{0}:{1}".format(pp_key, content))
        self.Debug("payload:")
        self.extract_payload(p)

    def consume_request(self, channel, method, properties, body):
        # json format load
        data = json.loads(body)

        # TODO: Message Controller
        if not self.silent_mode:
            self.Debug("Receive {0}".format(data))

        # email handler
        try:
            self.email_handler(data["data"])
        except Exception as e:
            self.Debug(e)

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

        # send response backto default exchanger
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
            self.Debug("Sent {0} to {1}".format(msg, properties.reply_to))

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        # wait for request, and do not allow other consumers on current queue
        self.channel.basic_consume(self.consume_request,
                queue=self.request_queue_id)

        # dispatch consume_request using start_consuming(), iteratively
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        self.Debug("Waiting for messages. To exit press CTRL+C")
        self.channel.start_consuming()

# start receiver
if __name__ == "__main__":
    args = sys.argv
    try:
        if len(args) == 4:
            r = requests.get("http://{localhost}:60666/routingkey")
            data = r.json()
            C = receiver(exchange_id="mail", routing_key=data["routing_key"], host="hostname", vhost=args[1], user=args[2], password=args[3])
            C.run()
        elif len(args) == 6:
            C = receiver(exchange_id=args[1], routing_key=args[2], vhost=args[3], user=args[4], password=args[5])
            C.run()
        else:
            print("./recvmq.py [exchange_id] [routing_key] [vhost] [user] [password]")
    except pika.exceptions.ProbableAuthenticationError as e:
        print(e)
    except Exception as e:
        print(e)
        print("./recvmq.py [exchange_id] [routing_key] [vhost] [user] [password]")
