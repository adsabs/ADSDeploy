import os
import sys
PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_HOME)
import boto3

from ADSDeploy import app
from ADSDeploy.models import Deployment

name_mapping = {
    'adsws': 'adsws',
    'biblib': 'biblib-service',
    'citation-helper': 'citation_helper_service',
    'export': 'export_service',
    'graphics': 'graphics_service',
    'harbour': 'harbour-service',
    'metrics': 'metrics_service',
    'myads': 'myads',
    'object': 'object_service',
    'orcid': 'orcid-service',
    'recommender': 'recommender_service',
    'vis': 'vis-services'
}

app.init_app()
client = boto3.client('elasticbeanstalk')

list_of_services = client.describe_environments(ApplicationName='sandbox')
for service in list_of_services['Environments']:

    name = service['VersionLabel'].split(':')[0].replace('-sandbox', '').replace('-services', '').replace('-service', '')
    tag = ':'.join(service['VersionLabel'].split(':')[1:])

    with app.session_scope() as session:
        deployment = Deployment(
            application='sandbox',
            environment=name_mapping[name],
            deployed=True,
            tested=False,
            msg='AWS bootstrapped',
            tag=tag
        )

        session.add(deployment)
        session.commit()

list_of_services = client.describe_environments(ApplicationName='eb-deploy')
for service in list_of_services['Environments']:

    name = service['VersionLabel'].split(':')[0].replace('-sandbox', '').replace('-services', '').replace('-service', '')
    tag = ':'.join(service['VersionLabel'].split(':')[1:])

    with app.session_scope() as session:
        deployment = Deployment(
            application='eb-deploy',
            environment=name_mapping[name],
            deployed=True,
            tested=False,
            msg='AWS bootstrapped',
            tag=tag
        )

        session.add(deployment)
        session.commit()
