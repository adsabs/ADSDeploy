#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no communication.
"""

import mock
import unittest

from ADSDeploy import app
from ADSDeploy.tests import test_base
from ADSDeploy.models import Base
from ADSDeploy.pipeline.deploy import Deploy, BeforeDeploy
from ADSDeploy.pipeline.workers import IntegrationTestWorker


class TestIntegrationWorker(unittest.TestCase):
    """
    Unit tests for the test integration worker
    """

    @mock.patch('ADSDeploy.pipeline.integration_tester.os.path.isdir')
    @mock.patch('ADSDeploy.pipeline.integration_tester.ChangeDirectory')
    @mock.patch('ADSDeploy.pipeline.integration_tester.shutil.rmtree')
    @mock.patch('ADSDeploy.pipeline.integration_tester.subprocess')
    @mock.patch('ADSDeploy.pipeline.integration_tester.git.Repo.clone_from')
    @mock.patch('ADSDeploy.pipeline.integration_tester.IntegrationTestWorker.publish')
    def test_worker_running_test(self, mocked_publish, mocked_clone, mocked_subprocess, mocked_rmtree, mocked_cd, mocked_isdir):
        """
        Test that the integration worker follows the expected workflow:
        """

        # Mock responses
        instance_cd = mocked_cd.return_value
        instance_cd.__enter__.return_value = instance_cd
        instance_cd.__exit__.return_value = None

        mocked_isdir.return_value = True
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
        result = worker.run_test(example_payload)

        # The worker downloads the repository that contains the integration
        # tests
        mocked_clone.assert_has_calls(
            [mock.call('https://github.com/adsabs/adsrex.git', '/tmp/adsrex')]
        )

        # The worker changes into the directory and runs the tests using
        # a bash script
        mocked_subprocess.Popen.assert_has_calls(
            [mock.call(['py.test'], stdin=mocked_subprocess.PIPE, stdout=mocked_subprocess.PIPE)]
        )

        # The test repository should also no longer exist
        mocked_rmtree.assert_has_calls(
            [mock.call('/tmp/adsrex')]
        )

        # The test passes and it forwards a packet on to the relevant worker,
        # with the updated keyword for test pass
        example_payload['test passed'] = True
        self.assertEqual(
            example_payload,
            result
        )

    @mock.patch('ADSDeploy.pipeline.integration_tester.os.path.isdir')
    @mock.patch('ADSDeploy.pipeline.integration_tester.ChangeDirectory')
    @mock.patch('ADSDeploy.pipeline.integration_tester.shutil.rmtree')
    @mock.patch('ADSDeploy.pipeline.integration_tester.subprocess')
    @mock.patch('ADSDeploy.pipeline.integration_tester.git.Repo.clone_from')
    @mock.patch('ADSDeploy.pipeline.integration_tester.IntegrationTestWorker.publish')
    def test_subprocess_raises_error(self, mocked_publish, mocked_clone, mocked_subprocess, mocked_rmtree, mocked_cd, mocked_isdir):
        """
        Test that nothing breaks if subprocess fails
        """

        # Mock responses
        instance_cd = mocked_cd.return_value
        instance_cd.__enter__.return_value = instance_cd
        instance_cd.__exit__.return_value = None

        mocked_isdir.return_value = True
        mocked_publish.return_value = None
        mocked_clone.return_value = None

        mocked_subprocess.Popen.side_effect = ValueError('ValueError')

        example_payload = {
            'application': 'staging',
            'service': 'adsws',
            'release': 'v1.0.0',
            'config': {},
            'action': 'test'
        }

        worker = IntegrationTestWorker()
        result = worker.run_test(example_payload.copy())

        # The worker downloads the repository that contains the integration
        # tests
        mocked_clone.assert_has_calls(
            [mock.call('https://github.com/adsabs/adsrex.git', '/tmp/adsrex')]
        )

        # The worker changes into the directory and runs the tests using
        # a bash script
        mocked_subprocess.Popen.assert_has_calls(
            [mock.call(['py.test'], stdin=mocked_subprocess.PIPE, stdout=mocked_subprocess.PIPE)]
        )

        # The test repository should also no longer exist
        mocked_rmtree.assert_has_calls(
            [mock.call('/tmp/adsrex')]
        )

        # The test passes and it forwards a packet on to the relevant worker,
        # with the updated keyword for test pass
        example_payload['test passed'] = False

        self.assertEqual(
            example_payload,
            result
        )

    @mock.patch('ADSDeploy.pipeline.integration_tester.os.path.isdir')
    @mock.patch('ADSDeploy.pipeline.integration_tester.ChangeDirectory')
    @mock.patch('ADSDeploy.pipeline.integration_tester.shutil.rmtree')
    @mock.patch('ADSDeploy.pipeline.integration_tester.subprocess')
    @mock.patch('ADSDeploy.pipeline.integration_tester.git.Repo.clone_from')
    @mock.patch('ADSDeploy.pipeline.integration_tester.IntegrationTestWorker.publish')
    def test_git_raises_error(self, mocked_publish, mocked_clone, mocked_subprocess, mocked_rmtree, mocked_cd, mocked_isdir):
        """
        Test that nothing breaks if subprocess fails
        """

        # Mock responses
        instance_cd = mocked_cd.return_value
        instance_cd.__enter__.return_value = instance_cd
        instance_cd.__exit__.return_value = None

        mocked_isdir.return_value = True
        mocked_publish.return_value = None
        mocked_clone.side_effect = ValueError('ValueError')

        example_payload = {
            'application': 'staging',
            'service': 'adsws',
            'release': 'v1.0.0',
            'config': {},
            'action': 'test'
        }

        worker = IntegrationTestWorker()
        result = worker.run_test(example_payload.copy())

        # The worker downloads the repository that contains the integration
        # tests
        mocked_clone.assert_has_calls(
            [mock.call('https://github.com/adsabs/adsrex.git', '/tmp/adsrex')]
        )

        # Subprocess should not be called
        self.assertFalse(mocked_subprocess.called)

        # Regardless, rmtree should still be called to cleanup any folders
        mocked_rmtree.assert_has_calls(
            [mock.call('/tmp/adsrex')]
        )

        # The test passes and it forwards a packet on to the relevant worker,
        # with the updated keyword for test pass
        example_payload['test passed'] = False

        self.assertEqual(
            example_payload,
            result
        )


class TestWorkers(test_base.TestUnit):
    """
    Tests the GenericWorker's methods
    """

    def tearDown(self):
        test_base.TestUnit.tearDown(self)
        Base.metadata.drop_all()
        app.close_app()

    def create_app(self):
        app.init_app({
            'SQLALCHEMY_URL': 'sqlite:///',
            'SQLALCHEMY_ECHO': False,
        })
        Base.metadata.bind = app.session.get_bind()
        Base.metadata.create_all()
        return app

    def test_deploy_BeforeDeploy(self):
        """Checks the worker has access to the AWS"""
        worker = BeforeDeploy()
        worker.process_payload({'application': 'sandbox', 'environment': 'adsws'})


if __name__ == '__main__':
    unittest.main()
