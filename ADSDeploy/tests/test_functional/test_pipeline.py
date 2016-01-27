"""
Functional test

Loads the ADSDeploy workers. It then injects input onto the RabbitMQ instance. Once
processed it then checks all things were written where they should. 
It then shuts down all of the workers.
"""


import unittest
import time
import json
from ADSDeploy.tests import test_base
from ADSDeploy.pipeline import generic
from ADSDeploy import app, models
import subprocess

class TestPipeline(test_base.TestFunctional):
    """
    Class for testing the overall functionality of the ADSDeploy pipeline.
    The interaction between the pipeline workers.
    
    Make sure you have the correct values set in the local_config.py
    These tests will use that config.
    """

    def example_test_forwarding(self):
        """Check the remote queue can receive a message from us
        
            You need to have `vagrant up imp` running
            and the user which starts the test have
            access to the docker
            
            This example is meant to show you how to test interaction
            between workers. It is not executable
        """
        
        # crude way of checking the rabbitmq is ready and queues are there
        init_state = subprocess.check_output('docker exec rabbitmq rabbitmqctl list_queues', shell=True)
        init_state = init_state.split()
        
        if 'FooBarDependency' not in init_state:
            raise Exception('Either you have not started vagrant imp or we cannot access the docker container rabbitmq')
        
        
        from pipeline import foo_bar  # @UnresolvedImport
        worker = foo_bar.FooBarWorker(params=app.config.get('WORKERS').get('FooBarWorker'))
        worker.connect(app.config.get('RABBITMQ_URL'))
        
        
        init_val = int(init_state[init_state.index('FooBarDependency') + 1])
        
        for x in range(100):
            worker.process_payload({
                                u'bibcode': u'2014ATel.6427....1V', 
                                u'unverified': [u'0000-0003-3455-5082', u'-', u'-', u'-', u'0000-0001-6347-0649']})
        
        # check that the worker has run
        fin_state = subprocess.check_output('docker exec rabbitmq rabbitmqctl list_queues', shell=True)
        fin_state = fin_state.split()
        fin_val = int(fin_state[init_state.index('FooBarDependency') + 1])
        
        self.assertGreater(fin_val, init_val, 'Hmm, seems like we failed to push updates to FooBarDependency')
        


    def example_test_pipeline(self):
        """
        Main test, it pretends we have received claims from the 
        ADSDeploy
        
        For this, you need to have 'db' and 'rabbitmq' containers running.
        :return: no return
        """
        
        # fire up the real queue
        self.TM.start_workers(verbose=True)
        
        # clean the slate (ie: delete stuff that might be laying there from the 
        # previous failed tests); this is just an example 
        with app.session_scope() as session:
            session.query(models.AuthorInfo).filter_by(orcidid='0000-0003-3041-2092').delete()
            session.query(models.ClaimsLog).filter_by(orcidid='0000-0003-3041-2092').delete()
            session.query(models.Records).filter_by(bibcode='2015ASPC..495..401C').delete()
            kv = session.query(models.KeyValue).filter_by(key='last.check').first()
            if kv is None:
                kv = models.KeyValue(key='last.check')
            kv.value = '2051-11-09T22:56:52.518001Z'
                
        # create anonymous worker with access to the exchange        
        test_worker = generic.RabbitMQWorker(params={
                            'publish': 'init-state',
                            'exchange': 'ADSDeploy-test-exchange'
                        })
        test_worker.connect(self.TM.rabbitmq_url)
        
        # send a test claim
        test_worker.publish({'orcidid': '0000-0003-3041-2092', 'bibcode': '2015ASPC..495..401C'})
        time.sleep(1)
        
        # check results
        with app.session_scope() as session:
            r = session.query(models.Records).filter_by(bibcode='2015ASPC..495..401C').first()
            self.assertEquals(json.loads(r.claims)['unverified'],
                              ['0000-0003-3041-2092', '-','-','-','-','-','-','-','-','-', ] 
                              )
            

if __name__ == '__main__':
    unittest.main()