#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests of the project. Each function related to the workers individual tools
are tested in this suite. There is no communication.
"""

import unittest

from datetime import datetime
from ADSDeploy import app
from ADSDeploy.models import Base, Deployment
from ADSDeploy.pipeline.workers import DatabaseWriterWorker


class TestDatabaseWriterWorker(unittest.TestCase):
    """
    Test the database writer worker
    """
    def create_app(self):
        app.init_app({
            'SQLALCHEMY_URL': 'sqlite://',
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
            'environment': 'adsws',
            'commit': 'latest-commit',
            'tag': 'latest-tag',
            'deployed': True,
            'tested': False,
        }

        worker = DatabaseWriterWorker()
        worker.process_payload(worker_payload)

        with self.app.session_scope() as session:
            deployment = session.query(Deployment).filter(
                Deployment.application == 'staging',
                Deployment.environment == 'adsws',
                Deployment.commit == 'latest-commit'
            ).one()

            for key in worker_payload:

                expected_value = worker_payload[key]
                stored_value = getattr(deployment, key)

                self.assertEqual(
                    expected_value,
                    stored_value,
                    msg='Attr "{}", expected value: "{}" != stored value: "{}"'
                        .format(key, expected_value, stored_value)
                )

            self.assertIsInstance(deployment.date_created, datetime)
            self.assertIsInstance(deployment.date_last_modified, datetime)

    def test_worker_overwrites_entry(self):
        """
        Test that the worker overwrites the relevant data in the database
        """

        # Stub the database entry
        with self.app.session_scope() as session:
            deployment = Deployment(
                application='staging',
                environment='adsws',
                commit='latest-commit',
                tag='latest-tag',
                deployed=True,
                tested=False
            )
            session.add(deployment)
            session.commit()

        worker_payload = {
            'application': 'staging',
            'environment': 'adsws',
            'commit': 'latest-commit',
            'tag': 'latest-tag',
            'deployed': True,
            'tested': True,
        }

        worker = DatabaseWriterWorker()
        worker.process_payload(worker_payload)

        with self.app.session_scope() as session:
            deployment = session.query(Deployment).filter(
                Deployment.application == 'staging',
                Deployment.environment == 'adsws',
                Deployment.commit == 'latest-commit'
            ).one()

            self.assertTrue(deployment.tested)
            self.assertTrue(
                deployment.date_last_modified > deployment.date_created
            )


if __name__ == '__main__':
    unittest.main()
