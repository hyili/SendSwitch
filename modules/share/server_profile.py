#!/usr/bin/env python3

class Server():
    def __init__(self, id, hostname, port):
        self.id = id
        self.hostname = hostname
        self.port = port
        self.statistic = 0

    def getId(self):
        return self.id

class Servers():
    def __init__(self, route_settings):
        self.registered_server_profile = dict()
        self.source_list = list()
        self.dest_list = list()
        self.exclusive = dict()
        self.default_route_settings = route_settings

    def getDefault(self):
        return self.default_route_settings

    def add(self, id=None, hostname=None, port=None, source=True, dest=True):
        if id and hostname:
            if id in self.registered_server_profile:
                return None
            else:
                server = Server(id, hostname, port)
                self.registered_server_profile[id] = server

        if source:
            self.addSource(id)

        if dest:
            self.addDest(id)

        return server

    def addSource(self, id):
        if id in self.registered_server_profile and id not in self.source_list:
            self.source_list.append(id)
            return id

        return None

    def addDest(self, id):
        if id in self.registered_server_profile and id not in self.dest_list:
            self.dest_list.append(id)
            return id

        return None

    def get(self, id):
        try:
            return self.registered_server_profile[id]
        except:
            return None

    def getSource(self, id):
        if id in self.source_list:
            return self.get(id)
        else:
            return None

    def getDest(self, id):
        if id in self.dest_list:
            return self.get(id)
        else:
            return None

    def addExclusive(self, id1, id2):
        self.exclusive[id1] = id2
        self.exclusive[id2] = id1

    def getExclusive(self, id):
        try:
            return self.exclusive[id]
        except:
            return None

    def checkExclusive(self, id1, id2):
        ret = self.getExclusive(id1)

        if ret is None:
            return None
        else:
            return ret == id2

    def delete(self, id):
        if self.get(id):
            self.registered_server_profile.pop(id)

        try:
            self.source_list.remove(id)
        except:
            pass

        try:
            self.dest_list.remove(id)
        except:
            pass

    def getList(self):
        return list(self.registered_server_profile)

    def getSourceList(self):
        return list(self.source_list)

    def getDestList(self):
        return list(self.dest_list)
