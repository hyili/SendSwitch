#!/usr/bin/env python3

import datetime
import pymysql
import sqlalchemy
from sqlalchemy import create_engine, update, and_, or_
from sqlalchemy.orm import sessionmaker, aliased

from model.user_route import UserRoute
from model.server import Server

class UserRoutes():
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

    def add(self, uid, source_id, destination_id):
        if not (uid and source_id and destination_id):
            return None

        route = self.get(uid, source_id)
        # if route exists
        if route:
            return None

        route = UserRoute(uid, source_id, destination_id)
        session = self.sessionmaker()
        try:
            session.add(route)
            session.commit()
            session.refresh(route)
        except Exception as e:
            session.rollback()
            route = None
            self.Debug("Something wrong happened during add(), reason: {0}.".format(e))

        session.close()

        return route

    def update(self, uid, source_id, destination_id):
        if not (uid and source_id and destination_id):
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(UserRoute).filter_by(uid=uid, source_id=source_id).\
                update({"destination_id": destination_id, "updated_at": datetime.datetime.utcnow()})
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            self.Debug("Something wrong happened during update(), reason: {0}.".format(e))

        session.close()

        return ret

    def get(self, uid, source_id):
        if not (uid and source_id):
            return None

        route = None
        session = self.sessionmaker()
        try:
            src = aliased(Server, name="src")
            dst = aliased(Server, name="dst")
            route = session.query(UserRoute, src, dst).\
                join(src, src.id==UserRoute.source_id).\
                join(dst, dst.id==UserRoute.destination_id).\
                filter(and_(UserRoute.uid == uid, UserRoute.source_id == source_id)).\
                one()
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            raise Exception("Database record error. {0}".format(e))
        except sqlalchemy.orm.exc.NoResultFound as e:
            route = None
        except Exception as e:
            route = None
            self.Debug("Something wrong happened during get(), reason: {0}.".format(e))

        session.close()

        return route

    def getUserRoutes(self, uid):
        if not uid:
            return None

        routes = None
        session = self.sessionmaker()
        try:
            src = aliased(Server, name="src")
            dst = aliased(Server, name="dst")
            routes = session.query(UserRoute, src, dst).\
                join(src, src.id==UserRoute.source_id).\
                join(dst, dst.id==UserRoute.destination_id).\
                filter(UserRoute.uid == uid).\
                all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            routes = list()
        except Exception as e:
            routes = None
            self.Debug("Something wrong happened during getUserRoutes(), reason: {0}.".format(e))

        session.close()

        return routes
