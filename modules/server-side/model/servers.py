#!/usr/bin/env python3

import datetime
import pymysql
import sqlalchemy
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker

from model.server import Server

class Servers():
    def __init__(self, logger, db_host, db_port, db_name, db_user, db_passwd):
        # create sqlalchemy ORM engine
        self.engine = create_engine("mysql+pymysql://{0}:{1}@{2}:{3}/{4}".\
            format(db_user, db_passwd, db_host, db_port, db_name), pool_recycle=3600)
        self.sessionmaker = sessionmaker(bind=self.engine)

        # try to connect to mysql
        self.engine.connect()

        # logger setup
        self.logger = logger

    def Debug(self, msg):
        self.logger.info(" [*] {0}".format(msg))

    def add(self, sid, hostname, port, source=True, dest=True, begin=False, end=False):
        if not (sid and hostname and port):
            return None

        server = self.get(sid)
        # if server exists
        if server:
            return None

        server = Server(sid, hostname, port, source, dest, begin, end, activate=True)
        session = self.sessionmaker()
        try:
            session.add(server)
            session.commit()
            session.refresh(server)
        except Exception as e:
            session.rollback()
            server = None
            self.Debug("Something wrong happened during add(), reason: {0}.".format(e))

        session.close()

        return server

    def get(self, sid):
        if not sid:
            return None

        server = None
        session = self.sessionmaker()
        try:
            server = session.query(Server).filter(Server.sid == sid).one()
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            raise Exception("Database record error. {0}".format(e))
        except sqlalchemy.orm.exc.NoResultFound as e:
            server = None
        except Exception as e:
            server = None
            self.Debug("Something wrong happened during get(), reason: {0}.".format(e))

        session.close()

        return server

    def getFromId(self, id):
        if not id:
            return None

        server = None
        session = self.sessionmaker()
        try:
            server = session.query(Server).filter(Server.id == id).one()
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            raise Exception("Database record error. {0}".format(e))
        except sqlalchemy.orm.exc.NoResultFound as e:
            server = None
        except Exception as e:
            server = None
            self.Debug("Something wrong happened during getFromId(), reason: {0}.".format(e))

        session.close()

        return server

    def delete(self, id):
        if not id:
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(Server).filter(Server.id==id).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            self.Debug("Something wrong happened during delete(), reason: {0}.".format(e))

        session.close()

        return ret

    def getList(self):
        servers = None
        session = self.sessionmaker()
        try:
            servers = session.query(Server).all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            servers = list()
        except Exception as e:
            servers = None
            self.Debug("Something wrong happened during getList(), reason: {0}.".format(e))

        session.close()
        
        return servers

    def getSourceList(self):
        servers = None
        session = self.sessionmaker()
        try:
            servers = session.query(Server).filter(Server.source == True).all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            servers = list()
        except Exception as e:
            servers = None
            self.Debug("Something wrong happened during getSourceList(), reason: {0}.".format(e))

        session.close()

        return servers

    def getDestList(self):
        servers = None
        session = self.sessionmaker()
        try:
            servers = session.query(Server).filter(Server.destination == True).all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            servers = list()
        except Exception as e:
            servers = None
            self.Debug("Something wrong happened during getDestList(), reason: {0}.".format(e))

        session.close()

        return servers
