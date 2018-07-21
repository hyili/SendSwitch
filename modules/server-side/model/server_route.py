#!/usr/bin/env python3

import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ServerRoute(Base):
    __tablename__ = "server_route"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer)
    destination_id = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    def __init__(self, source_id, destination_id):
        self.source_id = source_id
        self.destination_id = destination_id
        self.created_at = datetime.datetime.utcnow()
