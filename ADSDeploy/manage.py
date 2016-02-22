import os
import sys
PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_HOME)
import boto3

from ADSDeploy import app
from ADSDeploy.models import Deployment

app.init_app()
client = boto3.client('elasticbeanstalk')

for app in client.describe_applications()['Applications']:
    app_name = app['ApplicationName']
    
    list_of_services = client.describe_environments(ApplicationName=app_name)
    for service in list_of_services['Environments']:

        name = service['CNAME'].split('.')[0].replace('-{0}'.format(app_name), '')
        version = ':'.join(service['VersionLabel'].split(':')[1:])
    
        with app.session_scope() as session:
            deployment = Deployment(
                application=app_name,
                environment=name,
                deployed=service.get('Health', '') == 'Green',
                tested=False,
                msg='AWS bootstrapped',
                version=version
            )
    
            session.add(deployment)
            session.commit()
