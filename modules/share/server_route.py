#!/usr/bin/env python3

import datetime
import pymysql
import sqlalchemy
from sqlalchemy import create_engine, update, and_, or_
from sqlalchemy.orm import sessionmaker, aliased

from route import Route
from server import Server

class Routes():
    def __init__(self, db_host, db_port, db_name, db_user, db_passwd):
        # create sqlalchemy ORM engine
        self.engine = create_engine("mysql+pymysql://{0}:{1}@{2}:{3}/{4}".\
            format(db_user, db_passwd, db_host, db_port, db_name))
        self.sessionmaker = sessionmaker(bind=self.engine)

    def loop_check(self, uid, source_id, destination_id):
        # exclusive check

        # same with each other check
        if source_id == destination_id:
            return True

        # same with others check
        routes = self.getRoutes(uid)
        for route in routes:
            if route.source_id == source_id:
                continue

            if route.destination_id == destination_id:
                return True

        return False

    def add(self, uid, source_id, destination_id):
        if not (uid and source_id and destination_id):
            return None

        route = self.get(uid, source_id)
        if route:
            print("route {0} for user {1} exists.".format(source_id, uid))
            return None

        route = Route(uid, source_id, destination_id)
        session = self.sessionmaker()
        try:
            session.add(route)
            session.commit()
        except Exception as e:
            session.rollback()
            route = None
            print(e)

        session.close()

        return route

    def update(self, uid, source_id, destination_id):
        if not (uid and source_id and destination_id):
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(Route).filter_by(uid=uid, source_id=source_id).\
                update({"destination_id": destination_id, "updated_at": datetime.datetime.now()})
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            print(e)

        session.close()

        return ret

    def get(self, uid, source_id):
        if not (uid and source_id):
            return None

        route = None
        session = self.sessionmaker()
        try:
            src = aliased(Server, name="src")
            dest = aliased(Server, name="dest")
            route = session.query(Route, src, dest).\
                join(src, src.id==Route.source_id).\
                join(dest, dest.id==Route.destination_id).\
                filter(and_(Route.uid == uid, Route.source_id == source_id)).\
                one()
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            raise Exception("Database record error. {0}".format(e))
        except Exception as e:
            route = None
            print(e)

        session.close()

        return route

    def getRoutes(self, uid):
        if not uid:
            return None

        routes = None
        session = self.sessionmaker()
        try:
            src = aliased(Server, name="src")
            dest = aliased(Server, name="dest")
            routes = session.query(Route, src, dest).\
                join(src, src.id==Route.source_id).\
                join(dest, dest.id==Route.destination_id).\
                filter(Route.uid == uid).\
                all()
        except Exception as e:
            routes = None
            print(e)

        session.close()

        return routes
