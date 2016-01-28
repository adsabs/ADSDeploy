#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no communication.
"""

import mock
import unittest

from ADSDeploy.pipeline.workers import IntegrationTestWorker


class TestIntegrationWorker(unittest.TestCase):
    """
    Unit tests for the test integration worker
    """

    @mock.patch('ADSDeploy.pipeline.integration_tester.shutil.rmtree')
    @mock.patch('ADSDeploy.pipeline.integration_tester.subprocess')
    @mock.patch('ADSDeploy.pipeline.integration_tester.git.Repo.clone_from')
    @mock.patch('ADSDeploy.pipeline.integration_tester.IntegrationTestWorker.publish')
    def test_worker_running_test(self, mocked_publish, mocked_clone, mocked_subprocess, mocked_rmtree):
        """
        Test that the integration worker follows the expected workflow:
        """

        # Mock responses
        mocked_publish.return_value = None
        mocked_clone.return_value = None

        process = mock.Mock()
        process.communicate.return_value = '10 passed', ''
        mocked_subprocess.Popen.return_value = process

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

        # The test repository should also no longer exist
        mocked_rmtree.assert_has_calls(
            [mock.call('/tmp/adsrex')]
        )

        # The worker also places a database entry for the status change

        # The test passes and it forwards a packet on to the relevant worker,
        # with the updated keyword for test pass
        example_payload['test_passed'] = True
        mocked_publish.assert_has_calls(
            [mock.call(example_payload)]
        )

if __name__ == '__main__':
    unittest.main()
