

from .. import app
from generic import RabbitMQWorker
from ..models import Transaction


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
                'service': '',
                'active': '',
                'commit': '',
                'tag': '',
                'author': '',
                'worker': '',
                'before_deploy': '',
                'deploy': '',
                'test': '',
                'after_deploy': ''
            }
        :type msg: dict
        """

        required_attr = [
            'application',
            'service',
            'active',
            'commit',
            'tag',
            'author',
            'worker',
            'before_deploy',
            'deploy',
            'test',
            'after_deploy'
        ]

        result = dict(msg)

        # First check the payload is complete
        for attr in required_attr:
            if attr not in result:
                self.logger.error(
                    'Missing attribute "{}", not writing to database:  [{}]'
                    .format(attr, result)
                )
                raise KeyError

        # Write the payload to disk
        with self.app.session_scope() as session:

            transaction = Transaction()
            for attr in required_attr:
                setattr(transaction, attr, result[attr])

            try:
                session.add(transaction)
                session.commit()
            except Exception as err:
                self.logger.warning('Rolling back db entry: {}'.format(err))
                session.rollback()
