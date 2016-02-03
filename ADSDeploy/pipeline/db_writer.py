

from .. import app
from generic import RabbitMQWorker
from ..models import Deployment
from sqlalchemy.orm.exc import NoResultFound


class DatabaseWriterWorker(RabbitMQWorker):
    """
    Hello world example
    """
    def __init__(self, params=None):
        super(DatabaseWriterWorker, self).__init__(params)
        self.app = app
        self.app.init_app()

    def process_payload(self, msg, **kwargs):
        """
        :param msg: payload, must contain all of the values below:
            {
                'application': ''
                'environment': '',
                'commit': '',
                'tag': '',
                'deployed': '',
                'tested': '',
            }
        :type msg: dict
        """

        allowed_attr = [
            'application',
            'environment',
            'commit',
            'tag',
            'deployed',
            'tested',
        ]

        result = dict(msg)

        # Write the payload to disk
        with self.app.session_scope() as session:

            # Does the deployment already exist in the database, if so, find it
            try:
                deployment = session.query(Deployment).filter(
                    Deployment.application == 'staging',
                    Deployment.environment == 'adsws',
                    Deployment.commit == 'latest-commit'
                ).one()
            except NoResultFound:
                deployment = Deployment()

            # Either insert or update values
            for attr in allowed_attr:
                try:
                    setattr(deployment, attr, result[attr])
                except KeyError:
                    continue

            # Commit to the database or roll back
            try:
                session.add(deployment)
                session.commit()
            except Exception as err:
                self.logger.warning('Rolling back db entry: {}'.format(err))
                session.rollback()
