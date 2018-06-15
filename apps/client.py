#!/usr/bin/env python3

# TODO: Here is to solve security issue
# that RabbitMQ reveals in public network may cause problems

import sys

sys.path.append("../modules/client-side")
from config_loader import Config
from output import Output
from controller import Client_Controller
import web

# Output setup
output = Output()

# Config setup
config = Config(auth={"vhost": "test", "user": "test", "password": "test"},
    output=output)

# Controller setup
Controller = Client_Controller(config)

try:
    Controller.start()
    web.ManagementUI(config)

    print(" [*] Quit.")
    Controller.stop()
except KeyboardInterrupt:
    print(" [*] Signal Catched. Quit.")
    Controller.stop()
except Exception as e:
    print(e)
    Controller.stop()
