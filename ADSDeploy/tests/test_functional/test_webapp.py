"""
Functional test

Loads the ADSDeploy workers. It then injects input onto the RabbitMQ instance. Once
processed it then checks all things were written where they should. 
It then shuts down all of the workers.
"""


import unittest
import requests

from ADSDeploy.webapp.views import MiniRabbit
from ADSDeploy.config import RABBITMQ_URL, WEBAPP_URL


class TestWebApp(unittest.TestCase):
    """
    Test the interactions of the webapp with other services, such as RabbitMQ

    Note: this only works when assuming that the exchange set by RabbitMQ in
    the configuration file has been used. Specifically, EXCHANGE='test', and
    ROUTE='test', used to define the queue for the webapp.
    """

    def setUp(self):
        with MiniRabbit(RABBITMQ_URL) as w:
            w.make_queue('test')

    def tearDown(self):
        with MiniRabbit(RABBITMQ_URL) as w:
            w.delete_queue('test')

    def test_publishing_messages_to_queue(self):
        """
        Test that the end points publishes messages to the correct queue
        """

        url = 'http://{}/command'.format(WEBAPP_URL)

        params = {
            'application': 'staging',
            'environment': 'adsws',
            'version': 's23rfef3',
            'action': 'deploy'
        }

        r = requests.get(url, params=params)

        self.assertEqual(r.status_code, 200)

        self.assertEqual(r.json()['msg'], 'success')

        with MiniRabbit(RABBITMQ_URL) as w:
            messages = w.message_count(queue='test')
            packet = w.get_packet(queue='test')

        self.assertEqual(
            1,
            messages,
            msg='Expected 1 message, but found: {}'.format(messages)
        )

        self.assertEqual(
            packet,
            params,
            msg='Packet received {} != payload sent {}'.format(packet, params)
        )


if __name__ == '__main__':
    unittest.main()
