"""
Test webservices
"""

import json
import mock

from ADSDeploy.webapp import app
from flask import url_for
from flask.ext.testing import TestCase
from stub_data.stub_webapp import github_payload


class TestEndpoints(TestCase):
    """
    Tests http endpoints
    """
  
    def create_app(self):
        """
        Create the wsgi application
        """
        app_ = app.create_app()
        app_.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app_.config['DEPLOY_LOGGING'] = {}
        return app_

    def test_githublistener_endpoint(self):
        """
        Test basic functionality of the GithubListener endpoint
        """
        url = url_for('githublistener')

        r = self.client.get(url)
        self.assertStatus(r, 405)  # Method not allowed

        r = self.client.post(url)
        self.assertStatus(r, 400)  # No signature given


    @mock.patch('ADSDeploy.webapp.views.GithubListener.push_rabbitmq')
    @mock.patch('ADSDeploy.webapp.views.GithubListener.verify_github_signature')
    def test_githublistener_forwards_message(self, mocked_gh, mocked_rabbit):
        """
        Test that the GitHub listener passes the posted message to the
        relevant worker.
        """

        mocked_gh.return_value = True

        url = url_for('githublistener')

        r = self.client.post(url, data=github_payload)

        self.assertStatus(r, 200)
        self.assertEqual(
            r.json['received'],
            'adsws@bcdf7771aa10d78d865c61e5336145e335e30427:sandbox'
        )

        # Check RabbitMQ receives the expected payload
        expected_packet = {
            'repository': 'adsws',
            'commit': 'bcdf7771aa10d78d865c61e5336145e335e30427',
            'environment': 'sandbox',
            'author': 'vsudilov',
            'tag': None
        }

        mocked_rabbit.assert_called_once_with(expected_packet)

    @mock.patch('ADSDeploy.webapp.views.GithubListener')
    def test_rabbitmqlistener_forwards_message(self, mocked_gh):
        """
        Tests that the RabbitMQ parses and forwards the messages to the
        relevant queues
        """

        mocked_gh.push_rabbitmq.return_value = None

        url = url_for('rabbitmqlistener')

        payload = {
            'queue': 'deploy',
            'commit': '23d3f',
            'service': 'adsws'
        }

        r = self.client.post(url, data=json.dumps(payload))

        self.assertStatus(r, 200)
        self.assertEqual(r.json['msg'], 'success')

        mocked_gh.push_rabbitmq.assert_has_calls(
            [mock.call(payload)]
        )
