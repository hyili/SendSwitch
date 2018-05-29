#!/usr/bin/env python3

# TODO: Here is to solve security issue
# that RabbitMQ reveals in public network may cause problems

import sys
import asyncio

sys.path.append("../modules/client-side")
import web

async def test1():
    print("narukodo test1")

async def test2():
    print("narukodo test2")

loop = asyncio.new_event_loop()
loop.create_task(test1())
loop.run_until_complete(test2())
web.ManagementUI()
