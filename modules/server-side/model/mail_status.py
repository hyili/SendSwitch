#!/usr/bin/env python3

import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Mail(Base):
    __tablename__ = "mail_status"

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    corr_id = Column(String)
    status_code = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    def __init__(self, uid, corr_id, status_code):
        self.uid = uid
        self.corr_id = corr_id
        self.status_code = status_code
        self.created_at = datetime.datetime.utcnow()
