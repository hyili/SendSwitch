#!/usr/bin/env python3

import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Server(Base):
    __tablename__ = "server_profile"

    id = Column(Integer, primary_key=True)
    sid = Column(String)
    hostname = Column(String)
    port = Column(Integer)
    source = Column(Boolean)
    destination = Column(Boolean)
    begin = Column(Boolean)
    end = Column(Boolean)
    activate = Column(Boolean)
    created_at = Column(DateTime)
    activated_at = Column(DateTime)

    def __init__(self, sid, hostname, port, source, begin, end, destination, activate):
        self.sid = sid
        self.hostname = hostname
        self.port = port
        self.source = source
        self.destination = destination
        self.begin = begin
        self.end = end
        self.activate = activate
        self.created_at = datetime.datetime.utcnow()
        self.activated_at = datetime.datetime.utcnow() if activate else None
