#!/usr/bin/env python3

import pika
import json
import time
import datetime
import email
import requests

from protocols import Response
import macro
from processor import EmailDecodeProcessor, RedirectOutputProcessor

class Receiver():
    def __init__(self, timeout=600, exchange_id="random", routing_key="random", host="localhost", port=5672,
        processors=list(), silent_mode=False, vhost="/", credentials=None, user="guest", password="guest", output=None):

        # credentials
        if credentials is None:
            self.credentials = pika.PlainCredentials(user, password)
        else:
            self.credentials = credentials

        # rabbitmq host
        self.host = host
        self.port = port
        self.vhost = vhost
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

        # set some default processors
        self.ED_processor = EmailDecodeProcessor(description="Email Decoder Processor")
        self.RO_processor = RedirectOutputProcessor(description="Redirect Output Processor")
        self.RO_processor.set_output(output)

        # processors
        self.processors = processors

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

    # using user-defined processors to handle incoming email
    def email_handler(self, origin_msg, origin_result, processors):
        # result
        result = origin_result

        msg, result = self.ED_processor.run(origin_msg, result)
        msg, result = self.RO_processor.run(msg, result)
        for processor in processors:
            msg, result = processor.run(msg, result)

        return msg, result

    def consume_request(self, channel, method, properties, body):
        try:
            # json format load
            data = json.loads(body)

            # Debug message
            self.Debug("Receive {0}".format(data))

            # email handler
            current_processors = list(self.processors)
            msg, result = self.email_handler(data["data"], data["result"], current_processors)

            # resoponse message
            timestamp = time.time()
            # message will not actually be removed when times up
            # it will be removed until message head up the limit
            expire = self.timeout * 1000

            response = Response(timestamp=timestamp, expire=expire,
                result=result)

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
            # when error occurred, nack may cause infinite loop
            # channel.basic_nack(delivery_tag=method.delivery_tag)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            self.Debug(e)

    def reinit(self):
        self.__init__(timeout=self.timeout,
            exchange_id=self.exchange_id,
            routing_key=self.routing_key,
            host=self.host,
            port=self.port,
            processors=self.processors,
            silent_mode=self.silent_mode,
            vhost=self.vhost,
            credentials=self.credentials,
            output=self.output
        )

    def run(self):
        try:
            # wait for request, and do not allow other consumers on current queue
            self.channel.basic_consume(self.consume_request,
                queue=self.request_queue_id)

            # dispatch consume_request using start_consuming(), iteratively
            # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
            self.channel.start_consuming()
        except pika.exceptions.ConnectionClosed:
            self.Debug("Connection to rabbitmq closed, trying to reconnect.")
            try:
                self.reinit()
            except Exception as e:
                raise Exception("Failed to reconnect. {0}".format(e))
        except Exception as e:
            raise Exception("Error occurred. {0}".format(e))

    def close(self):
        self.Debug("Waiting for consumers to close.")
        self.channel.stop_consuming()
        self.connection.close()
