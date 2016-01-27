"""
Functional test

Loads the ADSDeploy workers. It then injects input onto the RabbitMQ instance. Once
processed it then checks all things were written where they should. 
It then shuts down all of the workers.
"""


import json
import unittest
import requests

from ADSDeploy.webapp.views import MiniRabbit
from ADSDeploy.config import RABBITMQ_URL, WEBAPP_URL


class TestWebApp(unittest.TestCase):
    """
    Test the interactions of the webapp with other services, such as RabbitMQ
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

        url = 'http://{}/rabbit'.format(WEBAPP_URL)

        payload = {
            'queue': 'deploy',
            'commit': '23d3f',
            'service': 'adsws',
            'route': 'test',
            'exchange': 'test'
        }

        r = requests.post(url, data=json.dumps(payload))

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

        # We do not expect exchange or route in the payload
        payload.pop('exchange')
        payload.pop('route')
        self.assertEqual(
            packet,
            payload,
            msg='Packet received {} != payload sent {}'.format(packet, payload)
        )


if __name__ == '__main__':
    unittest.main()
