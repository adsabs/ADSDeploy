"""
Integration Test Worker

carries out integration tests
"""

import os
import git
import shutil
import subprocess

from .. import app
from ..utils import ChangeDirectory
from generic import RabbitMQWorker
from collections import OrderedDict

ADS_REX_URL = 'https://github.com/adsabs/adsrex.git'
ADS_REX_BRANCH = 'develop'
ADS_REX_TMP = '/tmp/adsrex'
ADS_REX_PASS_KEYWORD = 'test passed'

ADS_REX_LOCAL_CONFIG = OrderedDict(
    API_BASE='https://devapi.adsabs.harvard.edu',
    AUTHENTICATED_USER_EMAIL='test@ads',
    AUTHENTICATED_USER_ACCESS_TOKEN='token',
    ORCID_OAUTH_ENDPOINT='https://sandbox.orcid.org/oauth/custom/login.json',
    ORCID_CLIENT_ID='',
    ORCID_USER='',
    ORCID_PASS=''
)


class IntegrationTestWorker(RabbitMQWorker):
    """
    Integration Test Worker

    Executes integration tests on the build that was deployed. These tests are
    currently fixed to being the ones found in adsrex:
        http://github.com/adsabs/adsrex.git

    Regardless of whether the tests pass, fail, or crash, the forwarding of the
    messages should still go to after_delpoy.
    """
    def __init__(self, params=None):
        super(IntegrationTestWorker, self).__init__(params)
        app.init_app()

    @staticmethod
    def make_local_config(config):
        """
        Hack to turn a dictionary into a single string
        :param config:
        """

        s = []
        for k, v in config.iteritems():
            if not isinstance(v, int) and not isinstance(v, float):
                s.append('{} = \'{}\''.format(k, v))
            else:
                s.append('{} = {}'.format(k, v))

        print s, config

        return '\n'.join(s)

    def run_test(self, msg):
        """
        Wrapper for easily testing the running of tests based on the payload

        ADSRex relies on a

        :param msg: input packet
        :type msg: dict

        :return: dict; modified packet based on test passing
        """

        try:
            # Step 1: download the repository that has the tests
            r = git.Repo.clone_from(ADS_REX_URL, ADS_REX_TMP, branch=ADS_REX_BRANCH)

            # Step 2: load the config for adsrex
            local_config = '{}/v1/local_config.py'.format(ADS_REX_TMP)
            if os.path.isdir(ADS_REX_TMP):
                with open(local_config, 'w') as f:
                    f.write(self.make_local_config(ADS_REX_LOCAL_CONFIG))

            # Step 2: run the tests via subprocess
            script = ['py.test']
            with ChangeDirectory(ADS_REX_TMP):
                p = subprocess.Popen(script, stdout=subprocess.PIPE, stdin=subprocess.PIPE)

            out, err = p.communicate()

            if 'ERRORS' in out or 'FAILURES' in out:
                msg[ADS_REX_PASS_KEYWORD] = False
            else:
                msg[ADS_REX_PASS_KEYWORD] = True

        except Exception as err:
            self.logger.error('IntegrationWorker: failed to process: {}'
                              .format(err))
            msg[ADS_REX_PASS_KEYWORD] = False

        finally:
            # Step 3: cleanup
            if os.path.isdir(ADS_REX_TMP):
                shutil.rmtree(ADS_REX_TMP)

        return msg

    def process_payload(self, msg, **kwargs):
        """
        :param msg: payload, example:
            {'foo': '....',
            'bar': ['.....']}
        :type: dict
        """

        # do something with the payload
        msg = dict(msg)
        result = IntegrationTestWorker.run_test(msg)

        # publish the results into the queue
        self.logger.info('Publishing to queue: {}'.format(self.publish_topic))
        self.publish(result)
