"""
Integration Test Worker

carries out integration tests
"""

import git
import shutil
import subprocess

from .. import app
from generic import RabbitMQWorker
from ..utils import ChangeDirectory

ADS_REX_URL = 'https://github.com/adsabs/adsrex.git'
ADS_REX_TMP = '/tmp/adsrex'


class IntegrationTestWorker(RabbitMQWorker):
    """
    Integration Test Worker
    """
    def __init__(self, params=None):
        super(IntegrationTestWorker, self).__init__(params)
        app.init_app()

    def process_payload(self, msg, **kwargs):
        """
        :param msg: payload, example:
            {'foo': '....',
            'bar': ['.....']}
        :type: dict
        
        :return: no return
        """

        self.logger.warning('Received packet: {}'.format(msg))

        if not isinstance(msg, dict):
            raise Exception('Received unknown payload {0}'.format(msg))
        
        if not msg.get('application'):
            raise Exception('Unusable payload, missing foo {0}'.format(msg))
        
        # do something with the payload
        result = dict(msg)        

        # Step 1: download the repository that has the tests
        git.Repo.clone_from(ADS_REX_URL, ADS_REX_TMP)

        # Step 2: run the tests via subprocess
        script = ['py.test']
        with ChangeDirectory(ADS_REX_TMP):
            p = subprocess.Popen(script, stdout=subprocess.PIPE, stdin=subprocess.PIPE)

        out, err = p.communicate()
        if 'ERRORS' or 'FAILURES' in out:
            result['test passed'] = False
        else:
            result['test passed'] = True

        # Step 3: cleanup
        shutil.rmtree(ADS_REX_TMP)

        # publish the results into the queue
        self.logger.info('Publishing to queue: {}'.format(self.publish_topic))
        self.publish(result)
