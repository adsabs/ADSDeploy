#!/usr/bin/env python
# encoding: utf-8

"""
Functional tests of the RabbitMQ Workers
"""

import json
import unittest

from ADSDeploy.pipeline.workers import IntegrationTestWorker
from ADSDeploy.webapp.views import MiniRabbit

RABBITMQ_URL = 'amqp://guest:guest@172.17.0.1:6672/?' \
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

    def tearDown(self):
        # Destroy queue
        with MiniRabbit(RABBITMQ_URL) as w:
            w.delete_queue('in', exchange='test')
            w.delete_queue('out', exchange='test')

    def test_workflow_of_integration_worker(self):
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
            'release': 'v1.0.0',
            'config': {},
            'action': 'test'
        }
        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(example_packet))

        # Worker runs the tests
        params = {
            'RABBITMQ_URL': RABBITMQ_URL,
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'out',
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

        example_packet['test_passed'] = True
        self.assertEqual(
            p,
            example_packet
        )

        # Worker updates the database for the relevant entries
        # Check entry here
