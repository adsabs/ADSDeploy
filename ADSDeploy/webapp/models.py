"""
Database models
"""

from ADSDeploy.models import Base, Deployment, KeyValue
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy(metadata=Base.metadata)
