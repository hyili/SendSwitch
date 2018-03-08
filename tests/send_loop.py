#!/usr/bin/env python3

import sys

sys.path.append("../modules")
import sendmq

sender = sendmq.sender("hello", ["world"])
for i in range(0, 1000, 1):
    sender.sendMsg("aaaaaa")
