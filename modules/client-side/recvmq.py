#!/usr/bin/env python3
import pika
import sys
import json
import time
import datetime
import email
import requests

from protocols import Response

class receiver():
    def __init__(self, timeout=600, exchange_id="random", routing_key="random", host="localhost", port=5672, processors=list(), silent_mode=False, vhost="/", user="guest", password="guest", output=None):
        # credentials
        self.credentials = pika.PlainCredentials(user, password)

        # rabbitmq host
        self.host = host
        self.port = port
        self.silent_mode = silent_mode

        # exchange_id & routing_key
        self.exchange_id = exchange_id
        self.routing_key = routing_key

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port, virtual_host=vhost, credentials=self.credentials))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)

        # declare request queue where request comes in
        self.request = self.channel.queue_declare(queue="mail",
            passive=True,
            arguments={
                "x-dead-letter-exchange": "return",
                "x-dead-letter-routing-key": "return"
            }
        )
        self.request_queue_id = self.request.method.queue

        self.timeout = timeout
        self.output = output

        # processors
        self.processors = processors

    def __del__(self):
        # close connection: after destruction
        try:
            self.channel.stop_consuming()
            self.connection.close()
        except Exception as e:
            self.Debug(e)

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    # using user-defined processors to handle incoming email
    def email_handler(self, origin_msg, processors):
        msg = self.redirect_output(origin_msg)
        for processor in processors:
            msg = processor.run(msg)

        return msg

    # redirect to web output
    def redirect_output(self, origin_msg):
        temp_msg = origin_msg

        try:
            if self.output is not None:
                json_msg = json.dumps(origin_msg)
                self.output.send(json_msg)
        except Exception as e:
            self.Debug("Error occurred during redirect_output.")
            self.Debug(e)
        finally:
            return origin_msg

    def consume_request(self, channel, method, properties, body):
        try:
            # json format load
            data = json.loads(body)

            # Debug message
            self.Debug("Receive {0}".format(data))

            # TODO: email handler
            current_processors = list(self.processors)
            msg = self.email_handler(data["data"], current_processors)

            # resoponse message
            timestamp = time.time()
            # message will not actually be removed when times up
            # it will be removed until message head up the limit
            expire = self.timeout * 1000

            # TODO: no need to response data now
            #response = Response(timestamp=timestamp, expire=expire,
            #    data=data["data"], reason=msg["reason"], result=msg["result"])
            response = Response(timestamp=timestamp, expire=expire,
                result=msg["result"])

            # send response backto default exchanger
            channel.basic_publish(exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=properties.correlation_id,
                    timestamp=int(timestamp),
                    expiration=str(expire),
                ),
                body=json.dumps(response.get())
            )
            # Message Controller
            if not self.silent_mode:
                self.Debug("Sent {0} to {1}".format(response.get(), properties.reply_to))

            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            # TODO: when error occurred, this may cause infinite loop
            # channel.basic_nack(delivery_tag=method.delivery_tag)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            self.Debug(e)

    def run(self):
        # wait for request, and do not allow other consumers on current queue
        self.channel.basic_consume(self.consume_request,
                queue=self.request_queue_id)

        # dispatch consume_request using start_consuming(), iteratively
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        self.Debug("Waiting for messages. To exit press CTRL+C")
        self.channel.start_consuming()

    def close(self):
        self.Debug("Waiting for consumers to close.")
        self.channel.stop_consuming()
        self.connection.close()
