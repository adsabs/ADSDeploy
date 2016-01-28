from ADSDeploy.pipeline.generic import RabbitMQWorker
from ADSDeploy import osutils, app
import os
from ADSDeploy.tests.test_unit.stub_data.stub_webapp import payload_tag


class BeforeDeploy(RabbitMQWorker):

    
    def process_payload(self, payload, 
        channel=None, 
        method_frame=None, 
        header_frame=None):
        """
        Receives information about the environment that
        is about to de deployed
        """
        
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
        
        
        # checks we can access the AWS and that the environment in question
        # is not busy
        x = osutils.Executioner(pyenv, app_home)
        r = x.cmd("./st")
        assert 'elasticbeanstalk.com' in r.out
        assert r.retcode == 0
        
        payload['eb'] = {'app_home': app_home, 'pyenv': pyenv}
        
        # we have to call publish otherwise nothing happens
        self.publish(payload)

        
class Deploy(RabbitMQWorker):
    
    def process_payload(self, payload, 
        channel=None, 
        method_frame=None, 
        header_frame=None):
        """Runs the actual deployment."""
        
        r = osutils.cmd("eb list")
        print r