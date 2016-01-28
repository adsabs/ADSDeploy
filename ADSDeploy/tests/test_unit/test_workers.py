#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no communication.
"""


import json
import re
import httpretty
import mock
import os
import unittest
import datetime
from dateutil import parser
from mock import patch

from ADSDeploy import app
from ADSDeploy.tests import test_base
from ADSDeploy.models import Base
from ADSDeploy.pipeline.workers import IntegrationTestWorker

#
# class TestWorkers(test_base.TestUnit):
#     """
#     Tests the GenericWorker's methods
#     """
#
#     def tearDown(self):
#         test_base.TestUnit.tearDown(self)
#         Base.metadata.drop_all()
#         app.close_app()
#
#     def create_app(self):
#         app.init_app({
#             'SQLALCHEMY_URL': 'sqlite:///',
#             'SQLALCHEMY_ECHO': False,
#         })
#         Base.metadata.bind = app.session.get_bind()
#         Base.metadata.create_all()
#         return app
#
#     @patch('ADSDeploy.pipeline.example.ExampleWorker.publish', return_value=None)
#     def test_example_worker(self, *args):
#         """Check it is publishing data"""
#         worker = ExampleWorker()
#         worker.process_payload({u'foo': u'bar', u'baz': [1,2]})
#         worker.publish.assert_called_with({u'foo': u'bar', u'baz': [1,2]})


class TestIntegrationWorker(unittest.TestCase):
    """
    Unit tests for the test integration worker
    """

    @mock.patch('ADSDeploy.pipeline.integration_tester.subprocess')
    @mock.patch('ADSDeploy.pipeline.integration_tester.git.Repo.clone_from')
    @mock.patch('ADSDeploy.pipeline.integration_tester.IntegrationTestWorker.publish')
    def test_worker_running_test(self, mocked_publish, mocked_clone, mocked_subprocess):
        """
        Test that the integration worker follows the expected workflow:
        """

        # Mock responses
        mocked_publish.return_value = None
        mocked_clone.return_value = None

        wait = mock.Mock(return_value=True)
        mocked_subprocess.Popen.return_value = wait

        example_payload = {
            'application': 'staging',
            'service': 'adsws',
            'release': 'v1.0.0',
            'config': {},
            'action': 'test'
        }

        worker = IntegrationTestWorker()
        worker.process_payload(example_payload)

        # The payload work flow is the following

        # The worker downloads the repository that contains the integration
        # tests
        mocked_clone.assert_has_calls(
            [mock.call('https://github.com/adsabs/adsrex.git', '/tmp/adsrex')]
        )

        # The worker changes into the directory and runs the tests using
        # a bash script
        mocked_subprocess.Popen.assert_has_calls(
            [mock.call(['pushd', '/tmp/adsrex', ';', 'py.test', ';', 'popd'])]
        )

        # The test passes and it forwards a packet on to the relevant worker,
        # with the updated keyword for test pass
        # example_payload['test_passed'] = True
        mocked_publish.assert_has_calls(
            [mock.call(example_payload)]
        )

        # The worker also places a database entry for the status change

if __name__ == '__main__':
    unittest.main()
