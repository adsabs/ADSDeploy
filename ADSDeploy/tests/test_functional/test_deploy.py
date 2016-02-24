#!/usr/bin/env python
# encoding: utf-8

"""
Functional tests of the RabbitMQ Workers
"""

import mock
import json
import unittest
import ADSDeploy.app as app

from ADSDeploy.pipeline.workers import Deploy, DatabaseWriterWorker
from ADSDeploy.webapp.views import MiniRabbit
from ADSDeploy.models import Base, Deployment

RABBITMQ_URL = 'amqp://guest:guest@172.17.0.1:6672/adsdeploy_test?' \
               'socket_timeout=10&backpressure_detection=t'


class TestDeployWorker(unittest.TestCase):
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
    def test_deploy_fails(self, mock_executioner):
        """
        Test that when the deploy fails the correct entries are sent and stored
        in the backend database
        """
        # Worker receives a packet, most likely from the webapp
        # Example packet:
        #
        #  {
        #    'application': 'staging',
        #    'environment': 'adsws',
        #    'version': 'v1.0.3'
        #  }
        #
        #
        packet = {
            'environment': 'adsws',
            'application': 'staging',
            'version': 'v1.0.0'
        }

        # Stub the database with some early entries
        first_deployment = Deployment(
            environment=packet['environment'],
            application=packet['application'],
            version='v0.0.1',
            deployed=True
        )
        with self.app.session_scope() as session:
            session.add(first_deployment)
            session.commit()

        # Override the run test returned value. This means the logic of the test
        # does not have to be mocked. retcode = 1 means it has failed
        mock_r = mock.Mock(retcode=1, command='r-command', err='r-err',
                           out='r-out')

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
        deploy_worker = Deploy(params=params)
        deploy_worker.run()
        deploy_worker.connection.close()

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
                .filter(Deployment.version == 'v1.0.0').one()
            self.assertEqual(
                deployment.msg,
                'staging-adsws deployment starts'
            )
            self.assertIsNone(deployment.deployed)

            deployment = session.query(Deployment)\
                .filter(Deployment.version == 'v0.0.1').one()
            self.assertTrue(deployment.deployed)

        db_worker.run()
        with self.app.session_scope() as session:
            deployment = session.query(Deployment)\
                .filter(Deployment.version == 'v1.0.0').one()

            for key in packet:
                self.assertEqual(
                    packet[key],
                    getattr(deployment, key)
                )
            self.assertFalse(deployment.deployed)
            self.assertEqual(
                deployment.msg,
                'deployment failed; command: r-command, reason: r-err, stdout: r-out'
            )

            deployment = session.query(Deployment)\
                .filter(Deployment.version == 'v0.0.1').one()

            self.assertTrue(deployment.deployed)

    @mock.patch('ADSDeploy.pipeline.deploy.create_executioner')
    def test_deploy_succeeds(self, mock_executioner):
        """
        Test that when the deploy succeeds the correct entries are sent and
        stored in the backend database
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
            'version': 'v1.0.0',
        }

        # Stub the database with some early entries
        first_deployment = Deployment(
            environment=packet['environment'],
            application=packet['application'],
            version='v0.0.1',
            deployed=True
        )
        with self.app.session_scope() as session:
            session.add(first_deployment)
            session.commit()

        # Override the run test returned value. This means the logic of the test
        # does not have to be mocked. retcode = 1 means it has failed
        mock_r = mock.Mock(retcode=0)

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
        deploy_worker = Deploy(params=params)
        deploy_worker.run()
        deploy_worker.connection.close()

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
                .filter(Deployment.version == 'v1.0.0').one()
            self.assertEqual(
                deployment.msg,
                'staging-adsws deployment starts'
            )
            self.assertIsNone(deployment.deployed)

            deployment = session.query(Deployment)\
                .filter(Deployment.version == 'v0.0.1').one()
            self.assertTrue(deployment.deployed)

        db_worker.run()
        with self.app.session_scope() as session:
            deployment = session.query(Deployment)\
                .filter(Deployment.version == 'v1.0.0').one()

            for key in packet:
                self.assertEqual(
                    packet[key],
                    getattr(deployment, key)
                )
            self.assertTrue(deployment.deployed)
            self.assertEqual(
                deployment.msg,
                'deployed'
            )

            deployment = session.query(Deployment)\
                .filter(Deployment.version == 'v0.0.1').one()
            self.assertFalse(deployment.deployed)
