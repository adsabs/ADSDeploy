#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no communication.
"""

import mock
import time
import unittest
import json
import os

from io import StringIO
from mock import Mock
from ADSDeploy import app
from ADSDeploy.tests import test_base
from ADSDeploy.models import Base, KeyValue
from ADSDeploy.pipeline.deploy import Deploy, BeforeDeploy, AfterDeploy, GithubDeploy


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
            'AFTER_DEPLOY_CLEANUP_TIME': 1,
            'EB_DEPLOY_HOME': '/dvt/workspace2/ADSDeploy/eb-deploy'
        })
        with app.session_scope() as session:
            Base.metadata.bind = session.get_bind()
            Base.metadata.create_all()
        return app

    @mock.patch('ADSDeploy.pipeline.deploy.os.path.exists')
    @mock.patch('ADSDeploy.pipeline.deploy.BeforeDeploy.publish')
    @mock.patch('ADSDeploy.osutils.Executioner.cmd', 
                return_value=Mock(**dict(retcode=0, 
                                         out='Ready adsws-sandbox.elasticbeanstalk.com adsws:v1.0.0:v1.0.2-17-g1b31375 Green adsws-sandbox')))
    def test_deploy_before_deploy(self, PatchedBeforeDeploy, exect, exists):
        """Checks the worker has access to the AWS"""
        # BeforeDeploy requires EB_DEPLOY path to exist
        exists.return_value = True

        worker = BeforeDeploy(params={'status': 'ads.deploy.status'})
        worker.process_payload({'application': 'sandbox', 'environment': 'adsws'})
        worker.publish.assert_has_calls([
            mock.call({'environment': 'adsws', 'application': 'sandbox', 'msg': 'OK to deploy'},topic='ads.deploy.deploy'),
            mock.call({'environment': 'adsws', 'application': 'sandbox', 'msg': 'OK to deploy'},topic='ads.deploy.status')
        ])

    def test_deploy_after_deploy(self):
        """Test after deploy"""
        worker = AfterDeploy()
        worker.process_payload({'application': 'sandbox', 'environment': 'adsws'})
        with app.session_scope() as sess:
            u = sess.query(KeyValue).first()
            assert u.toJSON()['key'] == u'sandbox.adsws.last-used'
            assert float(u.toJSON()['value']) < time.time() + 1
            assert float(u.toJSON()['value']) > time.time() - 1
            
    @mock.patch('ADSDeploy.pipeline.deploy.GithubDeploy.publish')
    
    def test_github_deploy(self, PatchedGithubDeploy):
        """Checks the github worker can deal with various inputs."""
        worker = GithubDeploy()
        
        
        with_sandbox = json.load(open(os.path.join(app.config.get('TEST_UNIT_DIR'), 
                                         'stub_data/os_walk_with_sandbox.json'), 'r'))
        without_sandbox = json.load(open(os.path.join(app.config.get('TEST_UNIT_DIR'), 
                                         'stub_data/os_walk_without_sandbox.json'), 'r'))
        
        def side_effect(x):
            if x == '/dvt/workspace2/ADSDeploy/eb-deploy/production/eb-deploy/adsws/repository':
                return StringIO(u'https://github.com/adsabs/adsws')
            elif x == '/dvt/workspace2/ADSDeploy/eb-deploy/sandbox/sandbox/adsws/repository':
                return StringIO(u'https://github.com/adsabs/adsws')
            else:
                return StringIO(u'foo')
            
        patched_open = mock.mock_open()
        patched_open.side_effect = side_effect
        
        with mock.patch("__builtin__.open", patched_open) as o:
            with mock.patch('os.walk', 
                return_value=without_sandbox) as m:
                worker.process_payload({'url': 'adsabs/adsws', 'tag': 'v1.0.1'})
                worker.publish.assert_called_once_with(
                   {'environment': u'adsws', 
                    'application': u'eb-deploy', 
                    'version': 'v1.0.1', 
                    'path': u'/dvt/workspace2/ADSDeploy/eb-deploy/production/eb-deploy/adsws'
                })
                worker.publish.reset_mock()
                
                worker.process_payload({'url': 'adsabs/adsws', 'tag': 'v1.0.1',
                                        'commit': 'abcd'})
                worker.publish.assert_called_once_with(
                   {'environment': u'adsws', 
                    'application': u'eb-deploy', 
                    'version': 'v1.0.1', 
                    'path': u'/dvt/workspace2/ADSDeploy/eb-deploy/production/eb-deploy/adsws'
                })
                worker.publish.reset_mock()
    
    
            with mock.patch('os.walk', 
                return_value=with_sandbox) as m:
                worker.process_payload({'url': 'adsabs/adsws', 'tag': 'v1.0.1'})
                worker.publish.assert_called_once_with(
                   {'environment': u'adsws', 
                    'application': u'sandbox', 
                    'version': 'v1.0.1', 
                    'path': u'/dvt/workspace2/ADSDeploy/eb-deploy/sandbox/sandbox/adsws'
                })
                worker.publish.reset_mock()
                
                worker.process_payload({'url': 'adsabs/adsws', 'tag': 'v1.0.1',
                                        'commit': 'abcd', 'application': 'eb-deploy'})
                worker.publish.assert_called_once_with(
                   {'environment': u'adsws', 
                    'application': u'eb-deploy', 
                    'version': 'v1.0.1', 
                    'path': u'/dvt/workspace2/ADSDeploy/eb-deploy/production/eb-deploy/adsws'
                })
                worker.publish.reset_mock()
            

if __name__ == '__main__':
    unittest.main()
