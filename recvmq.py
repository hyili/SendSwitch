#!/usr/bin/env python3
import pika
import sys

class client():
    def __init__(self, exchange_id, routing_key, queue_id="random"):
        # queue_id & exchange_id & routing_key
        self.queue_id = queue_id
        self.exchange_id = exchange_id
        self.routing_key = routing_key

        # connection to rabbitmq & channel declaration
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)

        # declare exchange
        self.channel.exchange_declare(exchange=self.exchange_id, exchange_type="direct")

        # declare request queue
        self.request = self.channel.queue_declare(queue=self.queue_id)

        # set queue bindings (can binds many keys to one queue)
        self.channel.queue_bind(exchange=self.exchange_id,
                queue=self.queue_id,
                routing_key=self.routing_key
        )

    def consume_request(self, channel, method, properties, body):
        print(" [*] Receive %s" % body)

        # resoponse message
        response = "Ok"

        # send response back WITHOUT exchanger
        channel.basic_publish(exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(
                    correlation_id = properties.correlation_id
                ),
                body=str(response)
        )
        print(" [*] Sent %s to %s" % (body, properties.reply_to))

        channel.basic_ack(delivery_tag = method.delivery_tag)

    def run(self):
        # wait for request
        self.channel.basic_consume(self.consume_request, queue=self.queue_id)

        # dispatch consume_request using start_consuming(), iteratively
        # http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html
        print(' [*] Waiting for messages. To exit press CTRL+C')
        self.channel.start_consuming()

# start client
if __name__ == "__main__":
    args = sys.argv
    if len(args) == 3:
        C = client(exchange_id=args[1], routing_key=args[2])
        C.run()
    else:
        print("./recvmq.py [exchange_id] [routing_key]")
