#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no communication.
"""

import unittest

from ADSDeploy import app
from ADSDeploy.tests import test_base
from ADSDeploy.models import Base
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
        })
        Base.metadata.bind = app.session.get_bind()
        Base.metadata.create_all()
        return app

    def test_deploy_BeforeDeploy(self):
        """Checks the worker has access to the AWS"""
        worker = BeforeDeploy()
        with self.assertRaises(Exception):
            worker.process_payload({'application': 'sandbox', 'environment': 'adsws'})


if __name__ == '__main__':
    unittest.main()
