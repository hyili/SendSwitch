#!/usr/bin/env python3

import sendmq

server = sendmq.server("hello", ["world"])
for i in range(0, 1000, 1):
    server.sendMsg("aaaaaa")
