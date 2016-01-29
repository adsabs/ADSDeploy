"""
Integration Test Worker

carries out integration tests
"""

import os
import git
import shutil
import subprocess

from .. import app
from generic import RabbitMQWorker
from ..utils import ChangeDirectory

ADS_REX_URL = 'https://github.com/adsabs/adsrex.git'
ADS_REX_TMP = '/tmp/adsrex'
ADS_REX_PASS_KEYWORD = 'test passed'


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

    def run_test(self, msg):
        """
        Wrapper for easily testing the running of tests based on the payload

        :param msg: input packet
        :type msg: dict

        :return: dict; modified packet based on test passing
        """

        try:
            # Step 1: download the repository that has the tests
            git.Repo.clone_from(ADS_REX_URL, ADS_REX_TMP)

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
