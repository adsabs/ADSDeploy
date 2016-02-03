#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no communication.
"""

import mock
import time
import unittest

from mock import Mock
from ADSDeploy import app
from ADSDeploy.tests import test_base
from ADSDeploy.models import Base, KeyValue
from ADSDeploy.pipeline.deploy import Deploy, BeforeDeploy, AfterDeploy


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
            'AFTER_DEPLOY_CLEANUP_TIME': 1
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

        worker = BeforeDeploy()
        worker.process_payload({'application': 'sandbox', 'environment': 'adsws'})
        worker.publish.assert_called_with({'environment': 'adsws', 'application': 'sandbox', 'msg': 'OK to deploy'})

    def test_deploy_after_deploy(self):
        """Test after deploy"""
        worker = AfterDeploy()
        worker.process_payload({'application': 'sandbox', 'environment': 'adsws'})
        with app.session_scope() as sess:
            u = sess.query(KeyValue).first()
            assert u.toJSON()['key'] == u'sandbox.adsws.last-used'
            assert float(u.toJSON()['value']) < time.time() + 1
            assert float(u.toJSON()['value']) > time.time() - 1

if __name__ == '__main__':
    unittest.main()
