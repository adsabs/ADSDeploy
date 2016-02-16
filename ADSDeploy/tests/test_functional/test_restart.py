#!/usr/bin/env python
# encoding: utf-8

"""
Functional tests of the RabbitMQ Workers
"""

import mock
import json
import unittest
import ADSDeploy.app as app

from ADSDeploy.pipeline.workers import Restart, DatabaseWriterWorker
from ADSDeploy.webapp.views import MiniRabbit
from ADSDeploy.models import Base, Deployment

RABBITMQ_URL = 'amqp://guest:guest@172.17.0.1:6672/adsdeploy_test?' \
               'socket_timeout=10&backpressure_detection=t'


class TestRestartWorker(unittest.TestCase):
    """
    Tests the functionality of the Before Deploy worker
    """
    def setUp(self):
        # Create queue
        with MiniRabbit(RABBITMQ_URL) as w:
            w.make_queue('in', exchange='test')
            w.make_queue('out', exchange='test')
            w.make_queue('database', exchange='test')
            w.make_queue('error', exchange='test')

        # Create database
        app.init_app({
            'SQLALCHEMY_URL': 'sqlite://',
            'SQLALCHEMY_ECHO': False,
        })
        Base.metadata.bind = app.session.get_bind()
        Base.metadata.create_all()
        self.app = app

    def tearDown(self):
        # Destroy queue
        with MiniRabbit(RABBITMQ_URL) as w:
            w.delete_queue('in', exchange='test')
            w.delete_queue('out', exchange='test')
            w.delete_queue('database', exchange='test')
            w.delete_queue('error', exchange='test')

        # Destroy database
        Base.metadata.drop_all()
        self.app.close_app()

    @mock.patch('ADSDeploy.pipeline.deploy.create_executioner')
    def test_restart_fails(self, mock_executioner):
        """
        Test that when a restart is requested, and the restart worker fails,
        the messages are updated
        """
        # Worker receives a packet, most likely from the webapp
        # Example packet:
        #
        #  {
        #    'application': 'staging',
        #    '....': '....',
        #  }
        #
        #
        packet = {
            'environment': 'staging',
            'application': 'adsws',
            'tag': 'v1.0.0',
            'commit': 'gf9gd8f',
        }

        # Override the run test returned value. This means the logic of the test
        # does not have to be mocked. retcode = 1 means it has failed
        mock_r = mock.MagicMock(retcode=1)
        mock_r.__str__.return_value = 'restart failed'

        mock_x = mock_executioner.return_value
        mock_x.cmd.return_value = mock_r

        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(packet))

        # Worker runs the tests
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'out',
            'header_frame': None,
            'error': 'error',
            'status': 'database',
            'TEST_RUN': True
        }
        restart_worker = Restart(params=params)
        restart_worker.run()
        restart_worker.connection.close()

        # Worker sends a packet to the next worker
        with MiniRabbit(RABBITMQ_URL) as w:
            self.assertEqual(w.message_count('in'), 0)
            self.assertEqual(w.message_count('out'), 0)
            self.assertEqual(w.message_count('database'), 2)
            self.assertEqual(w.message_count('error'), 1)

        # Start the DB Writer worker
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'database',
            'TEST_RUN': True
        }

        # First message should be starting of the deployment
        db_worker = DatabaseWriterWorker(params=params)
        db_worker.app = self.app
        db_worker.run()
        with self.app.session_scope() as session:
            deployment = session.query(Deployment)\
                .filter(Deployment.commit == 'gf9gd8f').one()
            self.assertEqual(
                deployment.msg,
                'staging-adsws restart-soft starts'
            )
            self.assertIsNone(deployment.deployed)

        db_worker.run()
        with self.app.session_scope() as session:
            deployment = session.query(Deployment)\
                .filter(Deployment.commit == 'gf9gd8f').one()

            for key in packet:
                self.assertEqual(
                    packet[key],
                    getattr(deployment, key)
                )
            self.assertFalse(deployment.deployed)
            self.assertEqual(
                deployment.msg,
                'restart failed'
            )

    @mock.patch('ADSDeploy.pipeline.deploy.create_executioner')
    def test_restart_succeeds(self, mock_executioner):
        """
        Test that when a restart is requested, and the restart worker succeeds,
        the messages are updated
        """
        # Worker receives a packet, most likely from the webapp
        # Example packet:
        #
        #  {
        #    'application': 'staging',
        #    '....': '....',
        #  }
        #
        #
        packet = {
            'environment': 'staging',
            'application': 'adsws',
            'tag': 'v1.0.0',
            'commit': 'gf9gd8f',
        }

        # Override the run test returned value. This means the logic of the test
        # does not have to be mocked. retcode = 1 means it has failed
        mock_r = mock.MagicMock(retcode=0)

        mock_x = mock_executioner.return_value
        mock_x.cmd.return_value = mock_r

        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(packet))

        # Worker runs the tests
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'out',
            'header_frame': None,
            'error': 'error',
            'status': 'database',
            'TEST_RUN': True
        }
        restart_worker = Restart(params=params)
        restart_worker.run()
        restart_worker.connection.close()

        # Worker sends a packet to the next worker
        with MiniRabbit(RABBITMQ_URL) as w:
            self.assertEqual(w.message_count('in'), 0)
            self.assertEqual(w.message_count('out'), 1)
            self.assertEqual(w.message_count('database'), 2)
            self.assertEqual(w.message_count('error'), 0)

        # Start the DB Writer worker
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'database',
            'TEST_RUN': True
        }

        # First message should be starting of the deployment
        db_worker = DatabaseWriterWorker(params=params)
        db_worker.app = self.app
        db_worker.run()
        with self.app.session_scope() as session:
            deployment = session.query(Deployment)\
                .filter(Deployment.commit == 'gf9gd8f').one()
            self.assertEqual(
                deployment.msg,
                'staging-adsws restart-soft starts'
            )
            self.assertIsNone(deployment.deployed)

        db_worker.run()
        with self.app.session_scope() as session:
            deployment = session.query(Deployment)\
                .filter(Deployment.commit == 'gf9gd8f').one()

            for key in packet:
                self.assertEqual(
                    packet[key],
                    getattr(deployment, key)
                )
            self.assertFalse(deployment.deployed)
            self.assertEqual(
                deployment.msg,
                'restart succeeded'
            )
