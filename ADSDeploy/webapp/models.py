"""
Database models
"""

from ADSDeploy.models import Base, Deployment
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy(metadata=Base.metadata)
