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
from ADSDeploy.pipeline.example import ExampleWorker

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
    
    @patch('ADSDeploy.pipeline.example.ExampleWorker.publish', return_value=None)
    def test_example_worker(self, *args):
        """Check it is publishing data"""
        worker = ExampleWorker()
        worker.process_payload({u'foo': u'bar', u'baz': [1,2]})
        worker.publish.assert_called_with({u'foo': u'bar', u'baz': [1,2]})
    
    

if __name__ == '__main__':
    unittest.main()        
        