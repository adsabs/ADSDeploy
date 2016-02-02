#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no communication.
"""

import mock
import unittest

from ADSDeploy import app
from ADSDeploy.models import Base, Transaction
from ADSDeploy.pipeline.workers import DatabaseWriterWorker


class TestDatabaseWriterWorker(unittest.TestCase):
    """
    Test the database writer worker
    """
    def create_app(self):
        app.init_app({
            'SQLALCHEMY_URL': 'sqlite:///',
            'SQLALCHEMY_ECHO': False,
        })
        Base.metadata.bind = app.session.get_bind()
        Base.metadata.create_all()
        return app

    def setUp(self):
        self.app = self.create_app()

    def tearDown(self):
        Base.metadata.drop_all()
        app.close_app()

    def test_worker_writes_to_database(self):
        """
        Test that the worker writes the relevant data to the database
        """
        worker_payload = {
            'application': 'staging',
            'service': 'adsws',
            'commit': 'latest-commit',
            'tag': 'latest-tag',
            'author': 'someone',
            'worker': 'ads.deploy.test',
            'before_deploy': True,
            'deploy': True,
            'test': False,
            'after_deploy': False,
            'active': False
        }

        worker = DatabaseWriterWorker()
        worker.process_payload(worker_payload)

        with self.app.session_scope() as session:
            transaction = session.query(Transaction).filter(
                Transaction.application == 'staging',
                Transaction.commit == 'latest-commit',
                Transaction.service == 'adsws'
            ).one()

            for key in worker_payload:

                expected_value = worker_payload[key]
                stored_value = getattr(transaction, key)

                self.assertEqual(
                    expected_value,
                    stored_value,
                    msg='Attr "{}", expected value: "{}" != stored value: "{}"'
                        .format(key, expected_value, stored_value)
                )

    def test_worker_raises_for_missing_fields(self):
        """
        Test that the worker fails safely if there are missing entries
        """
        worker_payload = {
            'application': 'staging',
            'service': 'adsws',
            'commit': 'latest-commit',
            'tag': 'latest-tag'
        }

        worker = DatabaseWriterWorker()

        with self.assertRaises(KeyError):
            worker.process_payload(worker_payload)

if __name__ == '__main__':
    unittest.main()
