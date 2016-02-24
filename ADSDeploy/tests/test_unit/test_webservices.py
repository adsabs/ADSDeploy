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
        app_.config['WEBAPP_EXCHANGE'] = 'unit-test-exchange'
        app_.config['WEBAPP_ROUTE'] = 'unit-test-route'
        return app_

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.drop_all()

    def test_githublistener_endpoint(self):
        """
        Test basic functionality of the GithubListener endpoint
        """
        url = url_for('githublistener')

        r = self.client.get(url)
        self.assertStatus(r, 405)  # Method not allowed

        r = self.client.post(url)
        self.assertStatus(r, 400)  # No signature given
        
    
    def test_storage_endpoint(self):
        """
        Test basic functionality of the ServerSideStorage endpoint
        """
        url = url_for('serversidestorage', key='foo')

        r = self.client.get(url)
        self.assertStatus(r, 200)
        self.assertEqual(r.json, {})
        
        r = self.client.post(url, data=json.dumps({'foo': 'bar'}), content_type='application/json')
        self.assertStatus(r, 200)
        self.assertEqual(r.json, {u'foo': u'bar'})
        
        r = self.client.get(url)
        self.assertStatus(r, 200)
        self.assertEqual(r.json, {u'foo': u'bar'})

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
            u'https://github.com/adsabs/adsws@bcdf7771aa10d78d865c61e5336145e335e30427:None'
        )

        # Check RabbitMQ receives the expected payload
        expected_packet = {
            'url': 'https://github.com/adsabs/adsws',
            'commit': 'bcdf7771aa10d78d865c61e5336145e335e30427',
            'author': 'vsudilov',
            'tag': None
        }

        mocked_rabbit.assert_has_calls(
            [mock.call(expected_packet, exchange='unit-test-exchange', route='unit-test-route')]
        )

    @mock.patch('ADSDeploy.webapp.views.GithubListener')
    def test_command_forwards_message_deploy(self, mocked_gh):
        """
        Test that the commands forwards messages properly
        """

        mocked_gh.push_rabbitmq.return_value = None

        params = {
            'application': 'staging',
            'version': '23d3f',
            'environment': 'adsws',
            'action': 'deploy'
        }

        url = url_for(
            'commandview',
            **params
        )

        r = self.client.get(url)

        self.assertStatus(r, 200)
        self.assertEqual(r.json['msg'], 'success')

        params['commit'] = params['version']
        mocked_gh.push_rabbitmq.assert_has_calls([mock.call(
            params,
            exchange='unit-test-exchange',
            route='unit-test-route'
        )])

    @mock.patch('ADSDeploy.webapp.views.GithubListener')
    def test_commandview_missing_payload(self, mocked_gh):
        """
        Test a 400 is raised if the user provides malformed data
        """

        mocked_gh.push_rabbitmq.return_value = None

        params = {
            'application': 'staging',
            'environment': 'adsws',
        }
        url = url_for(
            'commandview',
            **params
        )

        r = self.client.get(url)

        self.assertStatus(r, 400)

    def test_status_endpoint(self):
        """
        On request of the status, we wish to see a list of 'active' services,
        and their last N 'versions'
        """
        # Load the db with the entries we wish
        deployment1 = Deployment(
            environment='staging',
            application='adsws',
            version='commit-1',
            deployed=False,
            tested=True,
            status='success'
        )
        deployment2 = Deployment(
            environment='staging',
            application='adsws',
            version='commit-2',
            deployed=False,
            tested=True,
            status='success'
        )
        deployment3 = Deployment(
            environment='staging',
            application='adsws',
            version='commit-3',
            deployed=True,
            tested=True,
            status='success'
        )
        deployment4 = Deployment(
            environment='staging',
            application='graphics',
            version='commit-4',
            deployed=True,
            tested=True,
            status='success'
        )

        deployments = [deployment1, deployment2, deployment3, deployment4]
        db.session.add_all(deployments)
        db.session.commit()

        url = url_for('statusview')

        r = self.client.get(url)

        self.assertStatus(r, 200)

        expected_output = {
            'adsws': {
                'application': 'adsws',
                'environment': 'staging',
                'version': 'commit-3',
                'deployed': True,
                'tested': True,
                'previous_versions': ['commit-1', 'commit-2'],
                'active': ['commit-3'],
                'status': 'success'
            },
            'graphics': {
                'application': 'graphics',
                'environment': 'staging',
                'version': 'commit-4',
                'deployed': True,
                'tested': True,
                'active': ['commit-4'],
                'status': 'success'
            }
        }

        for output in r.json:
            expected = expected_output[output['application']]

            for key in expected:
                self.assertEqual(
                    expected[key],
                    output[key],
                    'Key "{}" expected "{}" != actual "{}"'
                    .format(key, expected[key], output[key])
                )


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
            version='v1.0.0',
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
            version='v1.0.0',
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

    def test_socket_connect(self):
        """
        Test that there is a FlaskSocketIO emit signal when the user connects
        to the Websocket. The user should receive all the deployments.
        """
        tmp_io_client = socketio.test_client(self.app, namespace='/status')
        emitted = tmp_io_client.get_received('/status')[0]

        self.assertEqual(emitted['namespace'], '/status')
        self.assertEqual(emitted['name'], 'connect')
        self.assertEqual(emitted['args'][0], 'connected')

        tmp_io_client.disconnect()
        emitted = tmp_io_client.get_received('/status')[0]
        self.assertEqual(emitted['args'][0], 'disconnected')
