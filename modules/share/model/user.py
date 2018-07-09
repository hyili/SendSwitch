#!/usr/bin/env python3

import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    account = Column(String)
    domain = Column(String)
    timeout = Column(Integer)
    service_ready = Column(Boolean)
    route_ready = Column(Boolean)
    created_at = Column(DateTime)
    service_ready_at = Column(DateTime)
    route_ready_at = Column(DateTime)

    # Flask-Login some attributes
    is_authenticated = Column(Boolean)
    is_active = Column(Boolean)
    is_anonymous = Column(Boolean)

    def __init__(self, email, timeout, service_ready, route_ready):
        self.account, self.domain = email.split("@")
        self.timeout = timeout
        self.service_ready = service_ready
        self.route_ready = route_ready
        self.created_at = datetime.datetime.now()

        # Flask-Login some attributes
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    # Flask-Login get_id method
    def get_id(self):
        return "{0}@{1}".format(self.account, self.domain)
