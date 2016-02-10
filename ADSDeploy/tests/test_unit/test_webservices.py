"""
Test webservices
"""

import json
import mock
import unittest

from ADSDeploy.webapp import app
from ADSDeploy.webapp.models import db, Deployment
from ADSDeploy.webapp.views import socketio
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
        app_.config['EXCHANGE'] = 'unit-test-exchange'
        app_.config['ROUTE'] = 'unit-test-route'
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

        mocked_rabbit.assert_has_calls(
            [mock.call(expected_packet, exchange='unit-test-exchange', route='unit-test-route')]
        )

    @mock.patch('ADSDeploy.webapp.views.GithubListener')
    def test_command_forwards_message_deploy(self, mocked_gh):
        """

        """

        mocked_gh.push_rabbitmq.return_value = None

        url = url_for('commandview')

        payload = {
            'application': 'staging',
            'commit': '23d3f',
            'environment': 'adsws',
        }

        r = self.client.post(url, data=json.dumps(payload))

        self.assertStatus(r, 200)
        self.assertEqual(r.json['msg'], 'success')

        mocked_gh.push_rabbitmq.assert_has_calls(
            [mock.call(payload, exchange='unit-test-exchange', route='unit-test-route')]
        )

    @mock.patch('ADSDeploy.webapp.views.GithubListener')
    def test_commandview_missing_payload(self, mocked_gh):
        """
        Test a 400 is raised if the user provides malformed data
        """

        mocked_gh.push_rabbitmq.return_value = None

        url = url_for('commandview')

        payload = {
            'application': 'staging',
            'environment': 'adsws',
        }

        r = self.client.post(url, data=json.dumps(payload))

        self.assertStatus(r, 400)


class TestSocketIONameSpaces(TestCase):
    """
    Test the WebSockets that are available from the application
    """
    def create_app(self):
        """
        Create the wsgi application
        """
        app_ = app.create_app()
        app_.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app_.config['DEPLOY_LOGGING'] = {}
        return app_

    def setUp(self):
        db.create_all()
        self.io_client = socketio.test_client(self.app, namespace='/status')
        self.connected = self.io_client.get_received('/status')[0]['name']

        assert self.connected == 'connect'

    def tearDown(self):
        self.io_client.disconnect()
        db.drop_all()
        db.session.remove()

    def test_socketio_db_event_insert(self):
        """
        Test that there is a FlaskSocketIO emit signal when there is an insert
        made to the database.
        """

        # Insert some value
        deployment = Deployment(
            application='adsws',
            environment='staging',
            tag='v1.0.0',
        )
        db.session.add(deployment)
        db.session.commit()

        emitted = self.io_client.get_received('/status')[0]

        self.assertEqual(emitted['namespace'], '/status')
        self.assertEqual(emitted['name'], 'database insert')

        expected_json = deployment.toJSON()
        for key, actual_value in emitted['args'][0].iteritems():
            self.assertEqual(
                expected_json[key],
                actual_value,
                msg='Expected, "[{}] = {}", but got "[{}] = "{}"'
                    .format(key, expected_json[key],
                            key, actual_value)
            )

    def test_socketio_db_event_update(self):
        """
        Test that there is a FlaskSocketIO emit signal when there is an update
        made to the database.
        """

        # Insert some value
        deployment = Deployment(
            application='adsws',
            environment='staging',
            tag='v1.0.0',
        )
        db.session.add(deployment)
        db.session.commit()

        # Ignore the emitting for the insert, we are interested in the update
        emitted = self.io_client.get_received('/status')
        del emitted

        deployment.deployed = True
        db.session.add(deployment)
        db.session.commit()

        emitted = self.io_client.get_received('/status')[0]

        self.assertEqual(emitted['namespace'], '/status')
        self.assertEqual(emitted['name'], 'database update')

        expected_json = deployment.toJSON()
        for key, actual_value in emitted['args'][0].iteritems():
            self.assertEqual(
                expected_json[key],
                actual_value,
                msg='Expected, "[{}] = {}", but got "[{}] = "{}"'
                    .format(key, expected_json[key],
                            key, actual_value)
            )

    def test_socketio_db_dump_on_connect(self):
        """
        Test that there is a FlaskSocketIO emit signal when the user connects
        to the Websocket. The user should receive all the deployments.
        """

        deployment_1 = Deployment(
            application='adsws',
            environment='staging',
            tag='v1.0.0',
        )
        deployment_2 = Deployment(
            application='graphics',
            environment='staging',
            tag='v0.0.9',
        )
        deployment_3 = Deployment(
            application='adsws',
            environment='production',
            tag='v1.0.1',
        )

        deployments = [deployment_1, deployment_2, deployment_3]
        db.session.add_all(deployments)
        db.session.commit()

        tmp_io_client = socketio.test_client(self.app, namespace='/status')
        emitted = tmp_io_client.get_received('/status')[0]

        self.assertEqual(emitted['namespace'], '/status')
        self.assertEqual(emitted['name'], 'connect')

        for i in [0, 1, 2]:
            expected_json = deployments[i].toJSON()
            for key, actual_value in emitted['args'][0][i].iteritems():
                self.assertEqual(
                    expected_json[key],
                    actual_value,
                    msg='Expected, "[{}] = {}", but got "[{}] = "{}"'
                        .format(key, expected_json[key],
                                key, actual_value)
                )
