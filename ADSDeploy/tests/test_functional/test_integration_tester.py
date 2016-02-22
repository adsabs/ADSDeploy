#!/usr/bin/env python
# encoding: utf-8

"""
Functional tests of the RabbitMQ Workers
"""

import mock
import json
import unittest
import ADSDeploy.app as app

from ADSDeploy.pipeline.workers import IntegrationTestWorker, \
    DatabaseWriterWorker
from ADSDeploy.webapp.views import MiniRabbit
from ADSDeploy.models import Base, Deployment

RABBITMQ_URL = 'amqp://guest:guest@172.17.0.1:6672/adsdeploy_test?' \
               'socket_timeout=10&backpressure_detection=t'


class TestIntegrationTestWorker(unittest.TestCase):
    """
    Tests the functionality of the Integration Worker
    """
    def setUp(self):
        # Create queue
        with MiniRabbit(RABBITMQ_URL) as w:
            w.make_queue('in', exchange='test')
            w.make_queue('out', exchange='test')
            w.make_queue('database', exchange='test')

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

        # Destroy database
        Base.metadata.drop_all()
        self.app.close_app()

    @mock.patch('ADSDeploy.pipeline.integration_tester.IntegrationTestWorker.run_test')
    def test_workflow_of_integration_worker(self, mock_run_test):
        """
        General work flow of the integration worker from receiving a packet,
        to finishing with a packet.
        """
        # Worker receives a packet, most likely from the deploy worker
        # Example packet:
        #
        #  {
        #    'application': 'staging',
        #    'service': 'adsws',
        #    'release': '',
        #    'config': {},
        #  }
        #
        #
        example_packet = {
            'application': 'staging',
            'service': 'adsws',
            'version': 'v1.0.0',
            'config': {},
            'action': 'test'
        }

        expected_packet = example_packet.copy()
        expected_packet['tested'] = True
        # Override the run test returned value. This means the logic of the test
        # does not have to be mocked
        mock_run_test.return_value = expected_packet

        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(example_packet))

        # Worker runs the tests
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'out',
            'status': 'database',
            'TEST_RUN': True
        }
        test_worker = IntegrationTestWorker(params=params)
        test_worker.run()
        test_worker.connection.close()

        # Worker sends a packet to the next worker
        with MiniRabbit(RABBITMQ_URL) as w:

            m_in = w.message_count(queue='in')
            m_out = w.message_count(queue='out')

            p = w.get_packet(queue='out')

        self.assertEqual(m_in, 0)
        self.assertEqual(m_out, 1)

        # Remove values that are not in the starting packet
        self.assertTrue(p.pop('tested'))
        self.assertEqual(
            p,
            example_packet
        )

    @mock.patch('ADSDeploy.pipeline.integration_tester.IntegrationTestWorker.run_test')
    def test_db_writes_on_test_pass(self, mocked_run_test):
        """
        Check that the database is being written to when a test passes
        """
        # Stub data
        packet = {
            'application': 'adsws',
            'environment': 'staging',
            'version': 'v1.0.0',
        }
        expected_packet = packet.copy()
        expected_packet['tested'] = True
        mocked_run_test.return_value = expected_packet

        # Start the IntegrationTester worker
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'out',
            'status': 'database',
            'TEST_RUN': True
        }

        # Push to rabbitmq
        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(packet))

        test_worker = IntegrationTestWorker(params=params)
        test_worker.run()
        test_worker.connection.close()

        # Assert there is a packet on the publish queue
        with MiniRabbit(RABBITMQ_URL) as w:
            self.assertEqual(w.message_count('out'), 1)
            self.assertEqual(w.message_count('database'), 1)

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
            self.assertEqual(deployment.tested, True)
