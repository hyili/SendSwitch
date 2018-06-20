#!/usr/bin/env python3

import threading

from recvmq import receiver

class Client_Controller():
    def __init__(self, config):
        self.config = config
        self.thread = None
        self.processors = self.config.kwargs["processors"]
        self.output = self.config.kwargs["output"]

        auth = self.config.kwargs["auth"]
        self.receiver = receiver(vhost=auth["vhost"], user=auth["user"], password=auth["password"], processors=self.processors, output=self.output)

    def __del__(self):
        if self.thread is not None:
            try:
                self.stop()
            except Exception as e:
                pass

    def run(self):
        try:
            self.receiver.run()
        except Exception as e:
            print(" [*] Something wrong during consumer setup. {0}".format(e))

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.receiver.close()
        self.thread.join()
        self.thread = None
