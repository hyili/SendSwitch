#!/usr/bin/env python3

class Config():
    # name, hostname, port
    def __init__(self, *args, **kwargs):
        self.nodes = dict()

        for arg in args:
            if type(arg) == tuple and len(arg) is 3:
                print(arg)
                self.nodes[arg[0]] = {"hostname": arg[1], "port": arg[2]}
            else:
                raise Exception("Type error. {0}.".format(arg))

        self.kwargs = kwargs
