# -*- coding: utf-8 -*-
import enum
import sqlalchemy
from flask import g

from citadel.ext import db
from citadel.models.base import BaseModelMixin, Enum34


class OPType(enum.Enum):
    REGISTER_RELEASE = 0
    BUILD_IMAGE = 1
    CREATE_ENV = 2
    DELETE_ENV = 3
    CREATE_CONTAINER = 4
    REMOVE_CONTAINER = 5
    UPGRADE_CONTAINER = 6
    CREATE_ELB_INSTANCE = 7
    CREATE_ELB_ROUTE = 8
    DELETE_ELB_ROUTE = 9


class OPLog(BaseModelMixin):

    __tablename__ = 'operation_log'
    zone = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    appname = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    sha = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    action = db.Column(Enum34(OPType))
    content = db.Column(db.JSON)

    @classmethod
    def get_by(cls, zone=None, appname=None, sha=None, action=None, time_window=None, start=0, limit=200):
        """filter OPLog by action, or a tuple of 2 datetime as timewindow"""
        try:
            filters = [(cls.zone == g.zone) | (cls.zone == '')]
        except AttributeError:
            filters = []

        if appname:
            filters.append(cls.appname == appname)

        if sha:
            filters.append(cls.sha.like('{}%'.format(sha)))

        if action:
            filters.append(cls.action == action)

        if time_window:
            left, right = time_window
            filters.extend([cls.created >= left, cls.created <= right])

        return cls.query.filter(sqlalchemy.and_(*filters)).order_by(cls.id.desc()).offset(start).limit(limit).all()

    @classmethod
    def generate_report(cls, type_, start=0, limit=20):
        """
        Sensible operation log report

        Args:
            type_ (str): choose from ('release')
        """
        if type_ == 'release':
            query = '''
            SELECT min(created) AS created, appname, sha, action
            FROM operation_log
            GROUP BY appname, sha, action
            ORDER BY created DESC
            '''
        else:
            raise Exception('Bad mode {}'.format(type_))
        res = [cls(**row) for row in db.session.execute(query).fetchall()]
        for obj in res:
            obj.action = OPType(obj.action)

        return res

    @classmethod
    def create(cls, action, appname='', sha='', zone='', content=None):
        if content is None:
            content = {}

        op_log = cls(zone=zone,
                     appname=appname,
                     sha=sha,
                     action=action,
                     content=content)
        db.session.add(op_log)
        db.session.commit()
        return op_log

    @property
    def verbose_action(self):
        return self.action.name

    @property
    def short_sha(self):
        return self.sha and self.sha[:7]
