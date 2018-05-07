#!/usr/bin/env python3

class Server():
    def __init__(self, id, hostname, port, settings=None):
        self.id = id
        self.hostname = hostname
        self.port = port
        self.settings = settings
        self.statistic = 0
        self.log = list()

class Servers():
    def __init__(self):
        self.registered_server_profile = dict()

    def add(self, id=None, hostname=None, port=None, server=None):
        if server:
            self.registered_server_profile[server.id] = server
        elif id and hostname:
            server = Server(id, hostname, port)
            self.registered_server_profile[id] = server

    def get(self, id):
        try:
            return self.registered_server_profile[id]
        except:
            return None

    def delete(self, id=None):
        if self.get(id):
            self.registered_server_profile.pop(id)

    def getAll(self):
        return list(self.registered_server_profile.keys())
