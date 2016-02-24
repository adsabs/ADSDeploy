"""
Functional test

Loads the ADSDeploy workers. It then injects input onto the RabbitMQ instance. Once
processed it then checks all things were written where they should. 
It then shuts down all of the workers.
"""


import os
import unittest

from ADSDeploy.tests import test_base
from ADSDeploy.pipeline import deploy
from ADSDeploy.pipeline.deploy import BeforeDeploy, Deploy, AfterDeploy
from mock import patch


class TestPipeline(test_base.TestFunctional):
    """
    Class for testing the overall functionality of the ADSDeploy pipeline.
    The interaction between the pipeline workers.
    
    Make sure you have the correct values set in the local_config.py
    These tests will use that config.
    """

    #@patch.object(BeforeDeploy, 'publish', lambda self, payload: self.channel.stop_consuming())
    def xtest_before_deploy_worker(self):
        """
        For this, you need to have 'db' and 'rabbitmq' containers running.
        :return: no return
        """
        def test(self, payload, *args, **kwargs):
            self.channel.stop_consuming()
            assert payload['environment'] == 'testing'
            assert payload['#done'][0] == 'before-deploy'
            
        with patch.object(BeforeDeploy, 'publish', test):
            worker = BeforeDeploy(params={'RABBITMQ_URL': self.TM.rabbitmq_url, 
                                          'subscribe': 'ads.deploy.before_deploy', 
                                          'exchange': 'ads-deploy-test-exchange'})
            self.test_publisher.publish({'application': 'sandbox', 'environment': 'testing'}, 
                                        topic='ads.deploy.before_deploy')
            worker.run()

    #@unittest.skipIf(
    #    not os.environ.get('EB_DEPLOY_HOME'),
    #    'Environment key "EB_DEPLOY_HOME" is missing.'
    #)
    def test_deploy_worker(self):
        """
        For this, you need to have 'db' and 'rabbitmq' containers running.
        :return: no return
        """
        payload = {'application': 'sandbox', 'environment': 'graphics'}
        x = deploy.create_executioner(payload)
        r = x.cmd('./find-env-by-attr url graphics')
        assert 'Ready' in r.out
        oldp = r.out.split()
        
        def test(self, payload, *args, **kwargs):
            if 'topic' in kwargs and kwargs['topic'] == 'ads.deploy.status':
                return
            
            print payload
            print kwargs
            
            try:
                assert payload['environment'] == 'graphics'
                assert payload['msg'] == 'deployed'
                r = x.cmd('./find-env-by-attr url graphics')
                newp = r.out.split()
                assert newp[1] == 'Ready'
                assert oldp[4] != newp[4]
            finally:
                self.channel.stop_consuming()
            
        with patch.object(Deploy, 'publish', test):
            worker = Deploy(params={'RABBITMQ_URL': self.TM.rabbitmq_url, 
                                          'subscribe': 'ads.deploy.deploy', 
                                          'exchange': 'ads-deploy-test-exchange'})
            self.test_publisher.publish(payload, 
                                        topic='ads.deploy.deploy')
            worker.run()        

if __name__ == '__main__':
    unittest.main()