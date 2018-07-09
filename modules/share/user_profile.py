#!/usr/bin/env python3

import datetime
import pymysql
import sqlalchemy
from sqlalchemy import create_engine, update, and_, or_
from sqlalchemy.orm import sessionmaker

from model.user import User

class Users():
    def __init__(self, db_host, db_port, db_name, db_user, db_passwd):
        # create sqlalchemy ORM engine
        self.engine = create_engine("mysql+pymysql://{0}:{1}@{2}:{3}/{4}".\
            format(db_user, db_passwd, db_host, db_port, db_name))
        self.sessionmaker = sessionmaker(bind=self.engine)

    def add(self, timeout, email):
        if not email:
            return None

        user = self.get(email)
        if user:
            print("user {0} exists.".format(email))
            return None

        user = User(email, timeout, service_ready=False, route_ready=True)
        session = self.sessionmaker()
        try:
            session.add(user)
            session.commit()
        except Exception as e:
            session.rollback()
            user = None
            print(e)

        session.close()

        return user

    def activateService(self, id):
        if not id:
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(User).filter_by(id=id).update(
                {"service_ready": True, "service_ready_at": datetime.datetime.now()}
            )
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            print(e)

        session.close()

        return ret

    def deactivateService(self, id):
        if not id:
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(User).filter_by(id=id).update(
                {"service_ready": False, "service_ready_at": datetime.datetime.now()}
            )
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            print(e)

        session.close()

        return ret

    def activateRoute(self, id):
        if not id:
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(User).filter_by(id=id).update(
                {"route_ready": True, "route_ready_at": datetime.datetime.now()}
            )
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            print(e)

        session.close()

        return ret

    def deactivateRoute(self, id):
        if not id:
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(User).filter_by(id=id).update(
                {"route_ready": False, "route_ready_at": datetime.datetime.now()}
            )
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            print(e)

        session.close()

        return ret

    def get(self, email):
        if not email:
            return None

        user = None
        session = self.sessionmaker()
        try:
            account, domain = email.split("@")
            user = session.query(User).filter(and_(User.account == account, User.domain == domain)).one()
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            raise Exception("Database record error. {0}".format(e))
        except Exception as e:
            user = None
            print(e)

        session.close()

        return user

    def getEmailList(self):
        emails = None
        session = self.sessionmaker()
        try:
            users = session.query(User.account, User.domain).all()
            emails = [ "{0}@{1}".format(user, domain) for user, domain in users ]
        except Exception as e:
            emails = None
            print(e)

        session.close()

        return emails

    def delete(self, id):
        if not id:
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(User).filter(User.id==id).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            print(e)

        session.close()

        return ret
