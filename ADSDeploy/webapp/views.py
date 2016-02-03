"""
Views
"""

import hashlib
import hmac
import json

import pika
from ADSDeploy.config import RABBITMQ_URL
from flask import current_app, request, abort
from flask.ext.restful import Resource

from .exceptions import NoSignatureInfo, InvalidSignature


class MiniRabbit(object):

    """
    Small context manager for simple interactions with RabbitMQ, without all of
    the boiler plate of a worker.
    """

    def __init__(self, url):
        self.connection = None
        self.channel = None
        self.url = url
        self.message = None

    def __enter__(self):
        self.connection = pika.BlockingConnection(pika.URLParameters(self.url))
        self.channel = self.connection.channel()
        self.channel.confirm_delivery()
        self.channel.basic_qos(prefetch_count=1)

        return self

    def __exit__(self, type, value, traceback):
        self.connection.close()

    def publish(self, payload, exchange, route):
        """
        Publish to a queue, on an exchange, with a specific route

        :param payload: payload to send to queue
        :type payload: dict

        :param exchange:rabbitmq exchange
        :type: exchange str

        :param route: rabbitmq route
        :type route: str
        """
        self.channel.basic_publish(exchange, route, payload)

    def message_count(self, queue):
        """
        Return the number of messages in the current queue

        :param queue: rabbitmq queue
        :type queue: str

        :return: int
        """
        q = self.channel.queue_declare(
            queue,
            passive=True
        )
        return q.method.message_count

    def get_packet(self, queue):
        """
        Get packet on queue

        :param queue: rabbitmq queue name
        :type queue: str

        :return: dict
        """
        packet = self.channel.basic_get(queue=queue, no_ack=True)
        try:
            packet = json.loads(packet[2])
        except:
            pass

        return packet

    def clear_queue(self, queue):
        """
        Empty the queue of all its packets

        :param queue: rabitmq queue name
        :type queue: str
        """
        self.channel.queue_purge(queue=queue)

    def delete_queue(self, queue, exchange=None):
        """
        Delete specified queue

        :param queue: rabbitmq queue name
        :type queue: str
        """
        exchange = queue if not exchange else exchange

        self.channel.queue_delete(queue=queue)
        self.channel.exchange_delete(exchange=exchange if not None else queue)

    def make_queue(self, queue, exchange=None):
        """
        Create a queue, its exchange, and route

        :param queue: desired queue name
        :type queue: str
        """

        exchange = queue if not exchange else exchange
        self.channel.exchange_declare(
            exchange=exchange,
            passive=False,
            durable=False,
            internal=False,
            type='topic',
            auto_delete=False
        )

        self.channel.queue_declare(
            queue=queue,
            passive=False,
            durable=False,
            auto_delete=False
        )

        self.channel.queue_bind(
            queue=queue,
            exchange=exchange,
            routing_key=queue
        )


class CommandView(Resource):
    """
    RabbitMQ Proxy
    """

    def post(self):
        """
        A proxy end point that forwards commands from the UI to the worker that
        makes the correct decision. It does minor checks on the keywords passed
        to the end point.
        """

        payload = request.get_json(force=True)

        required_keywords = [
            'application',
            'environment',
            'commit'
        ]

        for key in required_keywords:
            if key not in payload.keys():
                current_app.logger.error('Missing keyword "{}" from payload: {}'
                                         .format(key, payload))
                abort(400, 'Missing keyword: {}'.format(key))

        GithubListener.push_rabbitmq(
            payload,
            exchange=current_app.config.get('EXCHANGE'),
            route=current_app.config.get('ROUTE')
        )

        return {'msg': 'success'}, 200


class GithubListener(Resource):
    """
    GitHub web hook logic and routes
    """

    @staticmethod
    def verify_github_signature(request=None):
        """
        Validates the GitHub webhook signature

        :param request containing the header and body
        :type: flask.request object or None
        :return: None or raise
        """

        if request is None:
            raise NoSignatureInfo("No request object given")

        sig = request.headers.get(
            current_app.config.get('GITHUB_SIGNATURE_HEADER')
        )

        if sig is None:
            raise NoSignatureInfo("No signature header found")

        digestmod, sig = sig.split('=')

        h = hmac.new(
            current_app.config['GITHUB_SECRET'],
            msg=request.data,
            digestmod=hashlib.__getattribute__(digestmod),
        )

        if h.hexdigest() != sig:
            raise InvalidSignature("Signature not validated")

        return True

    @staticmethod
    def push_rabbitmq(payload, exchange, route):
        """
        Publishes the payload received from the GitHub webhooks to the correct
        queues on RabbitMQ.

        :param exchange: rabbitmq exchange
        :type exchange: str

        :param route: rabbitmq route
        :type route: str

        :param payload: GitHub webhook payload
        :type payload: dict
        """

        with MiniRabbit(RABBITMQ_URL) as w:
            w.publish(
                exchange=exchange,
                route=route,
                payload=json.dumps(payload)
            )

    @staticmethod
    def parse_github_payload(request=None):
        """
        parses a GitHub webhook message to create a models.Commit instance
        If that commit is already in the database, it instead returns that
        commit
        :param request: request containing the header and body
        :return: models.Commit based on the incoming payload
        """

        if request is None:
            raise ValueError("No request object given")

        formatted_request = request.get_json(force=True)

        payload = {
            'repository': formatted_request['repository']['name'],
            'commit': formatted_request['head_commit']['id'],
            'environment': 'sandbox',
            'author': formatted_request['head_commit']['author']['username'],
            'tag': formatted_request['ref'].replace('refs/tags/', '') \
            if 'tags' in formatted_request['ref'] else None
        }

        return payload

    def post(self):
        """
        Parse the incoming commit message, save to the backend database, and
        submit a build to the queue workers.

        This endpoint should be contacted by a GitHub webhook.
        """

        # Check the GitHub header for the correct signature
        try:
            GithubListener.verify_github_signature(request)
        except (NoSignatureInfo, InvalidSignature) as e:
            current_app.logger.warning("{}: {}".format(request.remote_addr, e))
            abort(400)

        try:
            payload = GithubListener.parse_github_payload(request)
        except Exception as error:
            return {'Exception: "{}"'.format(error)}, 400

        # Submit to RabbitMQ worker
        GithubListener.push_rabbitmq(payload, exchange=current_app.config.get('EXCHANGE'), route=current_app.config.get('ROUTE'))

        return {'received': '{}@{}:{}'.format(payload['repository'],
                                              payload['commit'],
                                              payload['environment'])}





