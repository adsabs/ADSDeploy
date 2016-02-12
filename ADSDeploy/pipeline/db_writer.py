"""
Database Writer
"""

from .. import app
from generic import RabbitMQWorker
from ..models import Deployment
from sqlalchemy.orm.exc import NoResultFound


class DatabaseWriterWorker(RabbitMQWorker):
    """
    Database Writer Worker
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
            'msg'
        ]

        result = dict(msg)

        # Write the payload to disk
        with self.app.session_scope() as session:

            # Does the deployment already exist in the database, if so, find it
            try:
                deployment = session.query(Deployment).filter(
                    Deployment.application == result['application'],
                    Deployment.environment == result['environment'],
                    Deployment.commit == result['commit']
                ).one()
            except NoResultFound:
                deployment = Deployment()
                self.logger.debug(
                    'No entry for <Deployment '
                    'environment: "{}", '
                    'application: "{}", '
                    'commit: "{}">'.format(
                        result['environment'],
                        result['application'],
                        result['commit']
                    )
                )

            except KeyError as error:
                self.logger.error('Missing uniquely identifying information '
                                  'for a record: {} [{}]'.format(error, msg))
                raise

            # New deployment?
            if not deployment.deployed and result.get('deployed', False):
                other_deployments = session.query(Deployment).filter(
                    Deployment.application == result['application'],
                    Deployment.environment == result['environment'],
                    Deployment.deployed == True,
                    Deployment.commit != result['commit'],
                    Deployment.tag != result['tag']
                ).all()

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

                for other in other_deployments:
                    other.deployed = False
                    session.add(other)
                    session.commit()

            except Exception as err:
                self.logger.warning('Rolling back db entry: {}'.format(err))
                session.rollback()
