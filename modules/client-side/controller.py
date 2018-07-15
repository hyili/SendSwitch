#!/usr/bin/env python3

import threading

from mq.recvmq import Receiver

class ClientController():
    def __init__(self, config, silent_mode=False):
        self.config = config
        self.thread = None
        self.interrupt_event = threading.Event()
        self.silent_mode = silent_mode

        self.processors = self.config.kwargs["processors"]
        self.output = self.config.kwargs["output"]
        self.retry_interval = self.config.kwargs["retry_interval"]

        self.receiver = None

    def __del__(self):
        if self.thread is not None:
            try:
                self.stop()
            except Exception as e:
                pass

    def Debug(self, msg):
        if not self.silent_mode:
            print(" [*] {0}".format(msg))

    def run(self):
        auth = self.config.kwargs["auth"]
        while True:
            try:
                self.receiver = Receiver(vhost=auth["vhost"], user=auth["user"], password=auth["password"], processors=self.processors, output=self.output)
                self.receiver.run()
                break
            except Exception as e:
                self.Debug("Error occurred during recvmq Receiver execution. {0}".format(e))
                self.Debug("Wait for restarting.")
                if self.interrupt_event.wait(timeout=self.retry_interval):
                    break
                self.Debug("Restarted.")

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.receiver:
            self.receiver.close()
        self.interrupt_event.set()
        self.thread.join()
        self.thread = None
