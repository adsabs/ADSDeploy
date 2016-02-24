#!/usr/bin/env python
# encoding: utf-8

"""
Functional tests of the RabbitMQ Workers
"""

import mock
import json
import unittest
import os
import ADSDeploy.app as app

from ADSDeploy.pipeline.workers import Deploy, DatabaseWriterWorker, GithubDeploy
from ADSDeploy.webapp.views import MiniRabbit
from ADSDeploy.models import Base, Deployment


class TestGithubDeploy(unittest.TestCase):
    """
    Tests the functionality of the Before Deploy worker
    """
    def setUp(self):
        # Create database
        app.init_app({
            'SQLALCHEMY_URL': 'sqlite://',
            'SQLALCHEMY_ECHO': False,
            'EB_DEPLOY_HOME': os.path.abspath('../../../eb-deploy')
        })
        
        # Create queue
        with MiniRabbit(app.config.get('RABBITMQ_URL')) as w:
            w.make_queue('in', exchange='test')
            w.make_queue('out', exchange='test')
            w.make_queue('database', exchange='test')
            w.make_queue('error', exchange='test')
            
        Base.metadata.bind = app.session.get_bind()
        Base.metadata.create_all()
        self.app = app

    def tearDown(self):
        # Destroy queue
        with MiniRabbit(app.config.get('RABBITMQ_URL')) as w:
            w.delete_queue('in', exchange='test')
            w.delete_queue('out', exchange='test')
            w.delete_queue('database', exchange='test')
            w.delete_queue('error', exchange='test')

        # Destroy database
        Base.metadata.drop_all()
        self.app.close_app()


    #@mock.patch('ADSDeploy.pipeline.deploy.create_executioner')
    def test_deploy_succeeds(self):
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
            'url': 'https://github.com/adsabs/adsws',
            'tag': 'v1.0.0',
            'application': 'eb-deploy'
        }


        with MiniRabbit(app.config['RABBITMQ_URL']) as w:
            w.publish(route='in', exchange='test', payload=json.dumps(packet))

        # Worker runs the tests
        params = {
            'RABBITMQ_URL': app.config['RABBITMQ_URL'],
            'exchange': 'test',
            'subscribe': 'in',
            'publish': 'out',
            'header_frame': None,
            'error': 'error',
            'status': 'database',
            'TEST_RUN': True
        }
        deploy_worker = GithubDeploy(params=params)
        deploy_worker.run()
        deploy_worker.connection.close()

        # Worker sends a packet to the next worker
        with MiniRabbit(app.config['RABBITMQ_URL']) as w:
            self.assertEqual(w.message_count('in'), 0)
            self.assertEqual(w.message_count('out'), 1)
            self.assertEqual(w.message_count('database'), 0)
            self.assertEqual(w.message_count('error'), 0)

