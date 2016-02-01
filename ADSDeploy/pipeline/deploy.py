from ADSDeploy.pipeline.generic import RabbitMQWorker
from ADSDeploy import osutils, app
import os
import time
import threading
from ADSDeploy.tests.test_unit.stub_data.stub_webapp import payload_tag
from __builtin__ import True


def create_executioner(payload):
    """From the information in the payload, create the Executioner."""
    assert 'application' in payload
    assert 'environment' in payload
    
    if not os.path.exists(os.path.abspath(app.config.get("EB_DEPLOY_HOME"))):
            raise Exception("The EB_DEPLOY_HOME is invalid")
        
    # identify the eb-deploy application home, usually root/<name>/<name>
    app_home = os.path.join(app.config.get('EB_DEPLOY_HOME'), payload['application'], 
                            payload['application'])
    
    if not os.path.exists(app_home):
        raise Exception('The {0} does not exist'.format(app_home))
    
    pyenv = app.config.get('EB_DEPLOY_VIRTUALENV', 
                         os.path.join(app.config.get('EB_DEPLOY_HOME'), 'python/bin/activate'))
    if not os.path.exists(pyenv):
        raise Exception('The EB_DEPLOY_VIRTUALENV is invalid')
    
    return osutils.Executioner(pyenv, app_home, app.config.get('MAX_WAIT_TIME', 30*60))


def is_timedout(payload, timestamp_key='timestamp'):
    """Make sure we are not running longer than MAX_WAIT_TIME."""
    if time.time() - payload.get(timestamp_key, time.time()) > app.config.get('MAX_WAIT_TIME', 30*60):
        return True
    return False
            
class BeforeDeploy(RabbitMQWorker):

    
    def process_payload(self, payload, 
        channel=None, 
        method_frame=None, 
        header_frame=None):
        """
        Receives information about the environment that
        is about to de deployed
        """
        
        if is_timedout(payload, timestamp_key='init_timestamp'):
            payload['err'] = 'timeout'
            payload['msg'] = 'BeforeDeploy: waiting too long for the environment to come up'
            return self.publish_to_error_queue(payload)
        
        x = create_executioner(payload)
        
        # checks we can access the AWS and that the environment in question
        # is not busy
        r = x.cmd("./find-env-by-attr url {0}".format(payload['environment']))
        assert r.retcode == 0
        
        for l in r.out.splitlines():
            parts = l.split()
            if len(parts) > 1 and parts[0] != 'Ready': # the environment is not ready, we have to wait
                
                # re-publish the payload to the queue, but do not block the worker
                def run(payload, worker):
                    if not 'init_timestamp' in payload:
                        payload['init_timestamp'] = time.time()
                    worker.publish(payload, topic=self.subscribe_topic)
                return threading.Timer(30, run, args=[payload, self]).start()
        
        # all is OK, we can proceed
        self.publish(payload)

        
class Deploy(RabbitMQWorker):
    
    def process_payload(self, payload, 
        channel=None, 
        method_frame=None, 
        header_frame=None):
        """Runs the actual deployment. It calls the eb-deploy safe-deploy.sh."""
        
        x = create_executioner(payload)
        
        r = x.cmd('./safe-deploy.sh {0}'.format(payload['environment']))
        if r.retcode == 0:
            self.publish(payload)
            payload['msg'] = 'deployed' 
            self.publish(payload, topic='ads.deploy.status')
        else:
            payload['err'] = 'deployment failed'
            payload['msg'] = 'command: {0}, reason: {1}, stdout: {2}'.format(r.command, r.err, r.out)
            self.publish_to_error_queue(payload)



class AfterDeploy(RabbitMQWorker):
    
    def process_payload(self, payload, 
        channel=None, 
        method_frame=None, 
        header_frame=None):
        """Runs the cleanup after the deployment happened."""
        
        x = create_executioner(payload)
        
        r = x.cmd('./safe-deploy.sh {0}'.format(payload['environment']))
        if r.retcode == 0:
            self.publish(payload)
        else:
            payload['err'] = 'deployment failed'
            payload['msg'] = 'command: {0}, reason: {1}, stdout: {2}'.format(r.command, r.err, r.out)
            self.publish_to_error_queue(payload)        