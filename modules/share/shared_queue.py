#!/usr/bin/env python3

import queue

class SharedQueue():
    def __init__(self, *args, queue_size=1000, **kwargs):
        self.kwargs = kwargs
        self.queue_size = queue_size
        self.queue = queue.Queue(queue_size)

    def send(self, msg):
        self.queue.put(msg, block=False)

    def recv(self):
        try:
            ret = self.queue.get(block=False)
        except queue.Empty as e:
            ret = None
        except Exception as e:
            print("Something wrong happened during ShardQueue.recv(), reason: {0}.".
                format(e))
            ret = None
        finally:
            return ret
