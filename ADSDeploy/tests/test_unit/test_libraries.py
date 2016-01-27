#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no pipeline communication.
"""


import sys
import os

import unittest
import json
import re
import os
import math
import httpretty
import mock
from io import BytesIO

from ADSDeploy.tests import test_base
from ADSDeploy import app, utils
from ADSDeploy.models import Base, KeyValue

class TestLibraries(test_base.TestUnit):
    """
    Tests the worker's methods
    """
    
    def tearDown(self):
        test_base.TestUnit.tearDown(self)
        Base.metadata.drop_all()
        app.close_app()
    
    def create_app(self):
        app.init_app({
            'SQLALCHEMY_URL': 'sqlite:///',
            'SQLALCHEMY_ECHO': False
        })
        Base.metadata.bind = app.session.get_bind()
        Base.metadata.create_all()
        return app
    
    def test_get_date(self):
        """Check we always work with UTC dates"""
        
        d = utils.get_date()
        self.assertTrue(d.tzname() == 'UTC')
        
        d1 = utils.get_date('2009-09-04T01:56:35.450686Z')
        self.assertTrue(d1.tzname() == 'UTC')
        self.assertEqual(d1.isoformat(), '2009-09-04T01:56:35.450686+00:00')
        
        d2 = utils.get_date('2009-09-03T20:56:35.450686-05:00')
        self.assertTrue(d2.tzname() == 'UTC')
        self.assertEqual(d2.isoformat(), '2009-09-04T01:56:35.450686+00:00')

        d3 = utils.get_date('2009-09-03T20:56:35.450686')
        self.assertTrue(d3.tzname() == 'UTC')
        self.assertEqual(d3.isoformat(), '2009-09-03T20:56:35.450686+00:00')


    def test_models(self):
        """Check serialization into JSON"""
        
        kv = KeyValue(key='foo', value='bar')
        self.assertDictEqual(kv.toJSON(),
             {'key': 'foo', 'value': 'bar'})
        
if __name__ == '__main__':
    unittest.main()
