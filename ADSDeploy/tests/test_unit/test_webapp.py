"""
Test utilities
"""

import hmac
import json
import mock
import hashlib
import unittest

from ADSDeploy.webapp import app
from ADSDeploy.webapp.models import db, Packet
from ADSDeploy.webapp.views import GithubListener
from stub_data.stub_webapp import github_payload, payload_tag
from ADSDeploy.webapp.utils import get_boto_session
from ADSDeploy.webapp.exceptions import NoSignatureInfo, InvalidSignature
from flask.ext.testing import TestCase


class FakeRequest:
    """
    A rudimentary mock flask.request object
    """
    def __init__(self):
        self.headers = {}
        self.data = ''

    def get_json(self, **kwargs):
        """
        return json from a string
        """
        self.json = json.loads(self.data)
        return self.json


class TestUtilities(unittest.TestCase):
    """
    Test utility functions in utils.py
    """

    @mock.patch('ADSDeploy.webapp.utils.Session')
    def test_get_boto_session(self, Session):
        """
        get_boto_session should call Session with the current app's config
        """
        app_ = app.create_app()
        app_.config['AWS_REGION'] = "unittest-region"
        app_.config['AWS_ACCESS_KEY'] = "unittest-access"
        app_.config['AWS_SECRET_KEY'] = "unittest-secret"
        with self.assertRaises(RuntimeError):  # app-context must be available
            get_boto_session()
        with app_.app_context():
            get_boto_session()
        Session.assert_called_with(
            aws_access_key_id="unittest-access",
            aws_secret_access_key="unittest-secret",
            region_name="unittest-region",
        )


class TestStaticMethodUtilities(TestCase):
    """
    Test standalone staticmethods
    """

    def create_app(self):
        """
        Create the wsgi application
        """
        app_ = app.create_app()
        app_.config['SQLALCHEMY_DATABASE_URI'] = "sqlite://"
        app_.config['GITHUB_SECRET'] = 'unittest-secret'
        app_.config['RABBITMQ_URL'] = 'rabbitmq'
        return app_

    def setUp(self):
        """
        setUp and tearDown are run at the start of each test; ensure
        that a fresh database is used for each test.
        """
        db.create_all()

    def tearDown(self):
        """
        setUp and tearDown are run at the start of each test; ensure
        that a fresh database is used for each test.
        """
        db.session.remove()
        db.drop_all()

    def test_verify_signature(self):
        """
        Ensures that the signature is validated against the github algorithim
        found at https://github.com/github/github-services/blob/f3bb3dd780feb6318c42b2db064ed6d481b70a1f/lib/service/http_helper.rb#L77
        """

        r = FakeRequest()

        r.data = '''{"payload": "unittest"}'''
        h = hmac.new(
            self.app.config['GITHUB_SECRET'],
            msg=r.data,
            digestmod=hashlib.sha1,
        ).hexdigest()
        r.headers = {
            'content-type': 'application/json',
            self.app.config['GITHUB_SIGNATURE_HEADER']: "sha1={}".format(h)
        }

        self.assertTrue(GithubListener.verify_github_signature(r))

        with self.assertRaises(InvalidSignature):
            r.data = ''
            GithubListener.verify_github_signature(r)

        with self.assertRaises(NoSignatureInfo):
            r.headers = {}
            GithubListener.verify_github_signature(r)

    def test_parse_github_payload(self):
        """
        Tests that a db.Commit object is created when passed an example
        github webhook payload
        """

        # Set up fake payload
        r = FakeRequest()
        r.data = github_payload.replace('"name": "adsws"', '"name": "mission-control"')

        # Modify the data such that the payload refers to a known repo,
        # assert that the returned models.Commit contains the expected data
        r.data = github_payload
        c = GithubListener.parse_github_payload(r)
        self.assertEqual(
            c['repository'],
            'adsws'
        )
        self.assertEqual(
            c['tag'],
            None
        )

        for key in ['repository', 'environment', 'commit', 'author', 'tag']:
            self.assertIn(
                key,
                c,
                msg='Key "{}" not found in "{}"'.format(key, c)
            )

    def test_parse_github_payload_tag(self):
        """
        Tests that a db.Commit object is created when passed a create event
        example github webhook payload
        """

        # Set up fake payload
        r = FakeRequest()
        r.data = payload_tag

        c = GithubListener.parse_github_payload(r)
        self.assertEqual(
            c['repository'],
            'adsws'
        )
        self.assertEqual(
            c['tag'],
            'v1.0.0'
        )

        for key in ['repository', 'environment', 'commit', 'author', 'tag']:
            self.assertIn(
                key,
                c,
                msg='Key "{}" not found in "{}"'.format(key, c)
            )

    @mock.patch('ADSDeploy.webapp.views.MiniRabbit')
    def test_payload_sent_to_rabbitmq(self, mocked_rabbit):
        """
        Tests that a payload is sent to rabbitmq and that it contains the
        expected payload.
        """

        instance_rabbit = mocked_rabbit.return_value
        instance_rabbit.__enter__.return_value = instance_rabbit
        instance_rabbit.__exit__.return_value = None
        instance_rabbit.publish.side_effect = None

        payload = {
            'exchange': 'test',
            'route': 'test',
            'repository': 'important-service',
            'commit': 'da89fuhds',
            'environment': 'staging',
            'author': 'author',
            'tag': 'da89fuhds',
        }
        payload_copy = payload.copy()

        GithubListener.push_rabbitmq(payload_copy)

        self.assertTrue(mocked_rabbit.called)

        c = instance_rabbit.publish.call_args[1]

        self.assertEqual(
            c['route'],
            payload.pop('route')
        )
        self.assertEqual(
            c['exchange'],
            payload.pop('exchange')
        )

        p = json.loads(c['payload'])
        for key in payload:
            self.assertEqual(
                payload[key],
                p.get(key, None),
                msg='key "{}" not found in call {}'.format(key, p)
            )
