# encoding: utf-8
"""
Database models
"""

from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime

Base = declarative_base()


class KeyValue(Base):
    """
    Example model, it stores key/value pairs - a persistent configuration
    """
    __tablename__ = 'storage'
    
    key = Column(String(255), primary_key=True)
    value = Column(Text)
    
    def toJSON(self):
        return {'key': self.key, 'value': self.value } 


class Transaction(Base):
    """
    Represents an entry from a worker
    """
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True)
    application = Column(String)
    service = Column(String)
    active = Column(Boolean, default=False)
    commit = Column(String)
    tag = Column(String)
    date_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    author = Column(String)
    worker = Column(String)
    before_deploy = Column(Boolean, default=False)
    deploy = Column(Boolean, default=False)
    test = Column(Boolean, default=False)
    after_deploy = Column(Boolean, default=True)

    def toJSON(self):
        """
        Convert to JSON
        :return: dict
        """
        return {
            'application': self.application,
            'service': self.service,
            'commit': self.commit,
            'tag': self.tag,
            'date_created': self.date_created,
            'author': self.author,
            'worker': self.worker,
            'before_deploy': self.before_deploy,
            'deploy': self.deploy,
            'test': self.test,
            'after_deploy': self.after_deploy,
        }

    def __repr__(self):
        return '<WorkerPacket (id: {}, commit: {}, tag: {}, timestamp: {}, ' \
               'author: {}, repository: {}, deployed: {}, tested: {}, ' \
               'environment: {}'.format(
                    self.id, self.commit, self.tag, self.timestamp, self.author,
                    self.repository, self.deployed, self.tested,
                    self.application
               )
