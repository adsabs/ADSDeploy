"""
Functional test

Loads the ADSDeploy workers. It then injects input onto the RabbitMQ instance. Once
processed it then checks all things were written where they should. 
It then shuts down all of the workers.
"""


import unittest
import time
import json
import sys
from ADSDeploy.tests import test_base
from ADSDeploy.pipeline import generic
from ADSDeploy.pipeline.deploy import BeforeDeploy
from ADSDeploy import app, models
import ADSDeploy.pipeline.deploy
import threading
from mock import patch, MagicMock

class TestPipeline(test_base.TestFunctional):
    """
    Class for testing the overall functionality of the ADSDeploy pipeline.
    The interaction between the pipeline workers.
    
    Make sure you have the correct values set in the local_config.py
    These tests will use that config.
    """


    #@patch.object(BeforeDeploy, 'publish', lambda self, payload: self.channel.stop_consuming())
    def test_before_deploy_worker(self):
        """
        For this, you need to have 'db' and 'rabbitmq' containers running.
        :return: no return
        """
        def test(self, payload, *args, **kwargs):
            self.channel.stop_consuming()
            assert payload['environment'] == 'testing'
            
        with patch.object(BeforeDeploy, 'publish', test):
            worker = BeforeDeploy(params={'RABBITMQ_URL': self.TM.rabbitmq_url, 
                                          'subscribe': 'ads.deploy.before_deploy', 
                                          'exchange': 'ads-deploy-test-exchange'})
            self.test_publisher.publish({'application': 'sandbox', 'environment': 'testing'}, topic='ads.deploy.before_deploy')
            worker.run()
        

if __name__ == '__main__':
    unittest.main()