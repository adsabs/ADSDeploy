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
        """
        Convert to JSON
        :return: dict
        """
        return {'key': self.key, 'value': self.value}


class Deployment(Base):
    """
    Represents an entry from a worker
    """
    __tablename__ = 'deployment'

    id = Column(Integer, primary_key=True)
    application = Column(String)
    environment = Column(String)
    commit = Column(String)
    tag = Column(String)
    date_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    date_last_modified = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    deployed = Column(Boolean, default=False)
    tested = Column(Boolean, default=False)

    def toJSON(self):
        """
        Convert to JSON
        :return: dict
        """
        return {
            'application': self.application,
            'environment': self.environment,
            'commit': self.commit,
            'tag': self.tag,
            'date_created': self.date_created,
            'date_last_modified': self.date_last_modified,
            'deployed': self.deployed,
            'tested': self.tested,
        }

    def __repr__(self):
        """
        String representation
        :return: str
        """
        _repr = [
            '\tapplication: {}'.format(self.application),
            '\tenvironment: {}'.format(self.environment),
            '\tcommit: {}'.format(self.commit),
            '\ttag: {}'.format(self.tag),
            '\tdate_created: {}'.format(self.date_created),
            '\tdate_last_modified: {}'.format(self.date_last_modified),
            '\tdeployed: {}'.format(self.deploy),
            '\ttested: {}'.format(self.test)
        ]

        return '<Deployment (\n{}\n)>'.format(', \n'.join(_repr))
