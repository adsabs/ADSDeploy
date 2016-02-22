#!/usr/bin/env python
# encoding: utf-8

"""
Functional tests of the RabbitMQ Workers
"""

import mock
import json
import unittest
import ADSDeploy.app as app

from ADSDeploy.pipeline.workers import BeforeDeploy, DatabaseWriterWorker
from ADSDeploy.webapp.views import MiniRabbit
from ADSDeploy.models import Base, Deployment

RABBITMQ_URL = 'amqp://guest:guest@172.17.0.1:6672/adsdeploy_test?' \
               'socket_timeout=10&backpressure_detection=t'


class TestBeforeDeployWorker(unittest.TestCase):
    """
    Tests the functionality of the Before Deploy worker
    """
    def setUp(self):
        # Create queue
        with MiniRabbit(RABBITMQ_URL) as w:
            w.make_queue('in', exchange='test')
            w.make_queue('ads.deploy.deploy', exchange='test')
            w.make_queue('ads.deploy.restart', exchange='test')
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
            w.delete_queue('ads.deploy.deploy', exchange='test')
            w.delete_queue('ads.deploy.restart', exchange='test')
            w.delete_queue('database', exchange='test')
            w.delete_queue('error', exchange='test')

        # Destroy database
        Base.metadata.drop_all()
        self.app.close_app()

    @mock.patch('ADSDeploy.pipeline.deploy.is_timedout')
    def test_before_deploy_fails(self, mock_is_timedout):
        """
        Test that the correct database entires are made by BeforeDeploy worker
        when the worker fails on its actions
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

        # Override the run test returned value. This means the logic of the test
        # does not have to be mocked
        mock_is_timedout.return_value = True

        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(packet))

        # Worker runs the tests
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'ads.deploy.deploy',
            'header_frame': None,
            'error': 'error',
            'status': 'database',
            'TEST_RUN': True
        }
        before_deploy_worker = BeforeDeploy(params=params)
        before_deploy_worker.run()
        before_deploy_worker.connection.close()

        # Worker sends a packet to the next worker
        with MiniRabbit(RABBITMQ_URL) as w:
            self.assertEqual(w.message_count('in'), 0)
            self.assertEqual(w.message_count('ads.deploy.deploy'), 0)
            self.assertEqual(w.message_count('database'), 1)
            self.assertEqual(w.message_count('error'), 1)

        # Start the DB Writer worker
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'database',
            'TEST_RUN': True
        }
        db_worker = DatabaseWriterWorker(params=params)
        db_worker.app = self.app
        db_worker.run()
        db_worker.connection.close()

        with self.app.session_scope() as session:

            all_deployments = session.query(Deployment).all()
            self.assertEqual(
                len(all_deployments),
                1,
                msg='More (or less) than 1 deployment entry: {}'
                    .format(all_deployments)
            )
            deployment = all_deployments[0]

            for key in packet:
                self.assertEqual(
                    packet[key],
                    getattr(deployment, key)
                )
            self.assertEqual(deployment.deployed, False)
            self.assertEqual(
                deployment.msg,
                'BeforeDeploy: waiting too long for the environment to come up'
            )

    @mock.patch('ADSDeploy.pipeline.deploy.create_executioner')
    def test_before_deploy_passes(self, mock_executioner):
        """
        Test that the correct database entires are made by BeforeDeploy worker
        when the worker succeeds on its actions
        """
        # Worker receives a packet, most likely from the webapp
        # Example packet:
        #
        #  {
        #    'application': 'staging',
        #    '....': '....',
        #  }a
        #
        #
        packet = {
            'environment': 'staging',
            'application': 'adsws',
            'version': 'v1.0.0',
        }

        # Override the run test returned value. This means the logic of the test
        # does not have to be mocked
        mock_r = mock.Mock(retcode=0)
        mock_r.out.splitlines.return_value = []

        mock_x = mock_executioner.return_value
        mock_x.cmd.return_value = mock_r

        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(packet))

        # Worker runs the tests
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'ads.deploy.deploy',
            'header_frame': None,
            'status': 'database',
            'error': 'error',
            'status': 'database',
            'TEST_RUN': True
        }
        before_deploy_worker = BeforeDeploy(params=params)
        before_deploy_worker.run()
        before_deploy_worker.connection.close()

        # Worker sends a packet to the next worker
        with MiniRabbit(RABBITMQ_URL) as w:
            self.assertEqual(w.message_count('in'), 0)
            self.assertEqual(w.message_count('ads.deploy.deploy'), 1)
            self.assertEqual(w.message_count('database'), 1)
            self.assertEqual(w.message_count('error'), 0)

        # Start the DB Writer worker
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'database',
            'TEST_RUN': True
        }
        db_worker = DatabaseWriterWorker(params=params)
        db_worker.app = self.app
        db_worker.run()
        db_worker.connection.close()

        with self.app.session_scope() as session:

            all_deployments = session.query(Deployment).all()
            self.assertEqual(
                len(all_deployments),
                1,
                msg='More (or less) than 1 deployment entry: {}'
                    .format(all_deployments)
            )
            deployment = all_deployments[0]

            for key in packet:
                self.assertEqual(
                    packet[key],
                    getattr(deployment, key)
                )
            self.assertEqual(deployment.deployed, None)
            self.assertEqual(
                deployment.msg,
                'OK to deploy'
            )

    @mock.patch('ADSDeploy.pipeline.deploy.create_executioner')
    def test_before_deploy_receives_restart(self, mock_executioner):
        """
        Test that the correct database entires are made by BeforeDeploy worker
        when the worker succeeds on its actions
        """
        # Worker receives a packet, most likely from the webapp
        # Example packet:
        #
        #  {
        #    'application': 'staging',
        #    '....': '....',
        #  }a
        #
        #
        packet = {
            'environment': 'staging',
            'application': 'adsws',
            'action': 'restart'
        }

        # Override the run test returned value. This means the logic of the test
        # does not have to be mocked
        mock_r = mock.Mock(retcode=0)
        mock_r.out.splitlines.return_value = []

        mock_x = mock_executioner.return_value
        mock_x.cmd.return_value = mock_r

        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(packet))

        # Worker runs the tests
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'ads.deploy.deploy',
            'header_frame': None,
            'status': 'database',
            'error': 'error',
            'status': 'database',
            'TEST_RUN': True
        }
        before_deploy_worker = BeforeDeploy(params=params)
        before_deploy_worker.run()
        before_deploy_worker.connection.close()

        # Worker sends a packet to the next worker
        with MiniRabbit(RABBITMQ_URL) as w:
            self.assertEqual(w.message_count('in'), 0)
            self.assertEqual(w.message_count('ads.deploy.deploy'), 0)
            self.assertEqual(w.message_count('ads.deploy.restart'), 1)
            self.assertEqual(w.message_count('database'), 1)
            self.assertEqual(w.message_count('error'), 0)

        # Start the DB Writer worker
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'database',
            'TEST_RUN': True
        }
        db_worker = DatabaseWriterWorker(params=params)
        db_worker.app = self.app
        db_worker.run()
        db_worker.connection.close()

        # remove irrelevant keys before checking things
        packet.pop('action')

        # check database entries
        with self.app.session_scope() as session:

            all_deployments = session.query(Deployment).all()
            self.assertEqual(
                len(all_deployments),
                1,
                msg='More (or less) than 1 deployment entry: {}'
                    .format(all_deployments)
            )
            deployment = all_deployments[0]

            for key in packet:
                self.assertEqual(
                    packet[key],
                    getattr(deployment, key)
                )
            self.assertEqual(deployment.deployed, None)
            self.assertEqual(
                deployment.msg,
                'Deploy to be restarted'
            )
