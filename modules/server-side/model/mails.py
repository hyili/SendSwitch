#!/usr/bin/env python3

import datetime
import pymysql
import sqlalchemy
from sqlalchemy import create_engine, update, and_, or_
from sqlalchemy.orm import sessionmaker

from model.mail_status import Mail

class Mails():
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

    def add(self, uid, corr_id):
        if not uid or not corr_id:
            return None

        mail = self.get(corr_id)
        # if mail exists
        if mail:
            return None

        mail = Mail(uid, corr_id, 0)
        session = self.sessionmaker()
        try:
            session.add(mail)
            session.commit()
            session.refresh(mail)
        except Exception as e:
            session.rollback()
            mail = None
            self.Debug("Something wrong happened during add(), reason: {0}.".format(e))

        session.close()

        return mail

    def get(self, corr_id):
        if not corr_id:
            return None

        mail = None
        session = self.sessionmaker()
        try:
            mail = session.query(Mail).filter(Mail.corr_id == corr_id).one()
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            raise Exception("Database record error. {0}".format(e))
        except sqlalchemy.orm.exc.NoResultFound as e:
            mail = None
        except Exception as e:
            mail = None
            self.Debug("Something wrong happened during get(), reason: {0}.".format(e))

        session.close()

        return mail

    def getFromUid(self, uid):
        mails = None
        session = self.sessionmaker()
        try:
            mails = session.query(Mail).filter(and_(Mail.uid == uid, Mail.status_code == 0)).all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            mails = list()
        except Exception as e:
            mails = None
            self.Debug(e)
            self.Debug("Something wrong happened during getFromUid(), reason: {0}.".format(e))

        session.close()

        return mails

    def updateMail(self, corr_id, status_code):
        if not corr_id or not status_code:
            return False

        ret = True
        session = self.sessionmaker()
        try:
            session.query(Mail).filter_by(corr_id=corr_id).update(
                {"status_code": status_code, "updated_at": datetime.datetime.utcnow()}
            )
            session.commit()
        except Exception as e:
            session.rollback()
            ret = False
            self.Debug("Something wrong happened during updateMail(), reason: {0}.".format(e))

        session.close()

        return ret
