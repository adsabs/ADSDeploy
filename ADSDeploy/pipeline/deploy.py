from ADSDeploy.pipeline.generic import RabbitMQWorker
from ADSDeploy import osutils, app
from ADSDeploy.models import KeyValue
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
    """Checks the environment before running the deployment. If the environment
    is in the 'pending' state, it will keep waiting MAX_WAIT_TIME.
    """
    
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
        payload['msg'] = 'OK to deploy'
        self.publish(payload)

        
class Deploy(RabbitMQWorker):
    """
    A wrapper around the eb-deploy's safe-deploy.sh script.
    We'll just execute the deployment and wait MAX_WAIT_TIME.
    On success, publish the payload. On failure, send it to
    the error queue.
    """
      
    def process_payload(self, payload, 
        channel=None, 
        method_frame=None, 
        header_frame=None):
        """Runs the actual deployment. It calls the eb-deploy safe-deploy.sh."""
        
        x = create_executioner(payload)
        self.publish({'msg': '{0}-{1} deployment starts'.format(payload['environment'], payload['application'])}, 
                      topic='ads.deploy.status')
        
        # this will run for a few minutes!
        r = x.cmd('./safe-deploy.sh {0} > /tmp/deploy.{0}.{1}'.format(payload['environment'], payload['application']))
        if r.retcode == 0:
            payload['msg'] = 'deployed'
            self.publish(payload) 
            self.publish({'msg': '{0}-{1} deployment finished'.format(payload['environment'], payload['application'])}, 
                      topic='ads.deploy.status')
        else:
            payload['err'] = 'deployment failed'
            payload['msg'] = 'command: {0}, reason: {1}, stdout: {2}'.format(r.command, r.err, r.out)
            self.publish_to_error_queue(payload)



class AfterDeploy(RabbitMQWorker):
    """After the deployment was finished, clean up the 
    AWS instances."""
    
    def process_payload(self, payload, 
        channel=None, 
        method_frame=None, 
        header_frame=None):
        """Runs the cleanup after the deployment happened."""
        
        # reset the timer
        key = 'testing.{0}.last-used'.format(payload['application'])
        now = time.time()
        with app.session_scope() as session:
            u = session.query(KeyValue).filter_by(key=key).first()
            if u is not None:
                u.value = now
            u = KeyValue(key, now)
            session.add(u)
            session.commit()
        
        def run(application, environment, key, old_now):
            # check something else did not update the timestamp in the meantime
            with app.session_scope() as session:
                u = session.query(KeyValue).filter_by(key=key).first()
                if u and time.time() + 1 - u.value > app.config.get('AFTER_DEPLOY_CLEANUP_TIME', 50*60):
                    x = create_executioner({'application': application, 'environment': environment})
                    r = x.cmd("./find-env-by-attr url testing")
                    to_terminate = []
                    for env in r.out.split():
                        parts = env.split()
                        to_terminate.append(parts[4])
                    for x in to_terminate:
                        x.cmd('eb terminate --force --nohang {0}'.format(x))
                
            
        threading.Timer(app.config.get('AFTER_DEPLOY_CLEANUP_TIME', 50*60), run, 
                        args=[payload['application'], payload['environment'], key, now]).start()
        
        
