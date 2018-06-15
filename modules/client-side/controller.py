#!/usr/bin/env python3

import threading

from recvmq import receiver

class Client_Controller():
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.thread = None
        self.handler = None

        self.output = self.config.kwargs["output"]

    def __del__(self):
        if self.thread is not None:
            try:
                self.stop()
            except Exception as e:
                pass

    def run(self):
        auth = self.config.kwargs["auth"]
        self.handler = receiver(vhost=auth["vhost"], user=auth["user"], password=auth["password"], output=self.output)
        self.handler.run()

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.handler.close()
        self.thread.join()
        self.thread = None
