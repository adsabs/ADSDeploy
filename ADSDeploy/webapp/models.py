"""
Database models
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Packet(db.Model):
    """
    Represents a git commit
    """
    id = Column(Integer, primary_key=True)
    commit = Column(String)
    tag = Column(String)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    author = Column(String)
    repository = Column(String)
    deployed = Column(Boolean, default=False)
    tested = Column(Boolean, default=False)
    application = Column(String)

    def __repr__(self):
        return '<Packet (id: {}, commit: {}, tag: {}, timestamp: {}, ' \
               'author: {}, repository: {}, deployed: {}, tested: {}, ' \
               'environment: {}'.format(
                    self.id, self.commit, self.tag, self.timestamp, self.author,
                    self.repository, self.deployed, self.tested,
                    self.application
               )
