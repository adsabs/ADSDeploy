"""
Views
"""


import hmac
import json
import pika
import boto3
import hashlib

from flask import current_app, request, abort
from flask.ext.restful import Resource
from flask.ext.socketio import SocketIO, emit

from .models import db, Deployment, KeyValue
from .exceptions import NoSignatureInfo, InvalidSignature

socketio = SocketIO()


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


class StatusView(Resource):
    """
    Status view
    """
    
    def get(self):
        """
        Return the list of active services. There should only be on active
        environment+application, with deployment.deployed == True. Deployments
        with deployment.deployed == False, are added to the 'previous_commits'
        key. Multiple active deployments is worrying, and any active deployments
        are included to the 'active' list. If there is more than 1, it means
        there is duplication, or an issue soemwhere.
        """

        client = boto3.client('elasticbeanstalk')

        aws_bootstrap = {}
        aws_identifiers = []

        applications = client.describe_applications()
        for application in applications['Applications']:
            app_name = application['ApplicationName']
            aws_bootstrap[app_name] = {}

            environments = client.describe_environments(ApplicationName=app_name)
            for environment in environments['Environments']:

                app = environment['ApplicationName']
                name = environment['CNAME'].split('.')[0].replace('-{0}'.format(app), '')
                version = ':'.join(environment['VersionLabel'].split(':')[1:])
                deployed = environment.get('Health', '') == 'Green'

                aws_bootstrap[app_name][name] = {
                    'version': version,
                    'deployed': deployed
                }

                aws_identifiers.append('{}@{}'.format(name, app))

        deployments = db.session.query(Deployment).all()

        # This is a bit more verbose, but it is more legible if some one else
        # were to read this code, rather than the optimised version that would
        # do a single request to the database

        identifiers = ['{}@{}'.format(
            deployment.environment, deployment.application
        ) for deployment in deployments]
        identifiers.extend(aws_identifiers)
        identifiers = list(set(identifiers))

        active = {}

        for identifier in identifiers:
            env, app = identifier.split('@')
            deployments = db.session.query(Deployment).filter(
                Deployment.environment == env,
                Deployment.application == app
            ).all()

            print 'trying', env, app

            if len(deployments) > 0:
                active[identifier] = {}
                active[identifier]['application'] = app
                active[identifier]['environment'] = env
                active[identifier]['previous_versions'] = []
                active[identifier]['active'] = []
                active[identifier]['version'] = None
                active[identifier]['deployed'] = False
                active[identifier]['tested'] = False
                active[identifier]['status'] = None

            else:
                if app not in aws_bootstrap or env not in aws_bootstrap[app]:
                    continue

                deployments = [Deployment(
                    application=app,
                    environment=env,
                    deployed=aws_bootstrap[app][env]['deployed'],
                    tested=False,
                    msg='AWS bootstrapped',
                    version=aws_bootstrap[app][env]['version']
                )]

                db.session.add(deployments[0])
                db.session.commit()

                active[identifier] = {}
                active[identifier]['application'] = app
                active[identifier]['environment'] = env
                active[identifier]['previous_versions'] = []
                active[identifier]['active'] = []
                active[identifier]['version'] = None
                active[identifier]['deployed'] = False
                active[identifier]['tested'] = False
                active[identifier]['status'] = None

            for deployment in deployments:

                if deployment.environment in aws_bootstrap[deployment.application] \
                  and deployment.version == aws_bootstrap[deployment.application][deployment.environment]['version'] \
                  and aws_bootstrap[deployment.application][deployment.environment]['deployed']:

                    active[identifier].update(deployment.toJSON())
                    active[identifier]['active'].append(deployment.version)
                else:
                    active[identifier]['previous_versions']\
                        .append(deployment.version)

            if not active[identifier]['active'] \
                    and env in aws_bootstrap[app] \
                    and aws_bootstrap[app][env]['deployed']:

                deployment = Deployment(
                    application=app,
                    environment=env,
                    deployed=aws_bootstrap[app][env]['deployed'],
                    tested=False,
                    msg='AWS bootstrapped',
                    version=aws_bootstrap[app][env]['version']
                )

                db.session.add(deployment)
                db.session.commit()

                active[identifier].update(deployment.toJSON())
                active[identifier]['active'].append(aws_bootstrap[app][env]['version'])

            print active[identifier], '\n'

        # Less verbose, a little more thought required to understand
        # active = {}
        # for deployment in deployments:
        #
        #     identifier = '{}-{}'.format(
        #         deployment.environment, deployment.application
        #     )
        #
        #     if deployment.deployed:
        #
        #         active.setdefault(identifier, {}).update(deployment.toJSON())
        #
        #         active[identifier].setdefault('active', [])\
        #             .append(deployment.commit)
        #
        #         continue
        #
        #     active.setdefault(identifier, {})\
        #         .setdefault('previous_versions', [])\
        #         .append(deployment.commit)

        return active.values(), 200


class ServerSideStorage(Resource):
    """
    For whatever the widget wants to store in the KeyValue store
    """
    
    def get(self, key):
        """
        Retrieves the key as stored in the database
        """
        key = 'ui:{0}'.format(key)
        kv = db.session.query(KeyValue).filter_by(key=key).first()
        if kv is None:
            return {}, 200
        else:
            v = kv.value and kv.value or '{}'
            return json.loads(v), 200
        
    def post(self, key):
        """Saves the data in the storage"""
        key = 'ui:{0}'.format(key)
        payload = request.get_json(force=True)
        out = None
        u = db.session.query(KeyValue).filter_by(key=key).first()
        if u is None:
            u = KeyValue(key=key, value=json.dumps(payload))
        db.session.add(u)
        db.session.commit()
        out = json.loads(u.value)
        return out, 200


class RabbitMQ(Resource):
    """
    RabbitMQ Testing Proxy
    """

    def post(self):
        """
        Generic RabbitMQ Proxy with no protection
        """

        payload = request.get_json(force=True)

        exchange = payload.pop('exchange')
        route = payload.pop('route')

        GithubListener.push_rabbitmq(
            payload,
            exchange=exchange,
            route=route
        )

        return {'msg': 'success'}, 200


class CommandView(Resource):
    """
    RabbitMQ Proxy
    """

    def get(self):
        """
        A proxy end point that forwards commands from the UI to the worker that
        makes the correct decision. It does minor checks on the keywords passed
        to the end point.
        """

        required_keywords = [
            'application',
            'environment',
            'version',
            'action'
        ]
        args = {k: request.args[k] for k in required_keywords}

        for key in required_keywords:
            if key not in args.keys():
                current_app.logger.error('Missing keyword "{}" from payload: {}'
                                         .format(key, args))
                abort(400, 'Missing keyword: {}'.format(key))

        # Currently, version is a synonym to commit
        args['commit'] = args['version']

        GithubListener.push_rabbitmq(
            args,
            exchange=current_app.config.get('WEBAPP_EXCHANGE'),
            route=current_app.config.get('WEBAPP_ROUTE')
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

        with MiniRabbit(current_app.config['RABBITMQ_URL']) as w:
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
            'url': formatted_request['repository']['url'],
            'commit': formatted_request['head_commit']['id'],
            'author': formatted_request['head_commit']['author']['username'],
            'tag': formatted_request['ref'].replace('refs/tags/', '')
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
        GithubListener.push_rabbitmq(
            payload,
            exchange=current_app.config.get('WEBAPP_EXCHANGE'),
            route=current_app.config.get('WEBAPP_ROUTE')
        )

        return {'received': '{}@{}:{}'.format(payload['url'],
                                              payload['commit'],
                                              payload['tag'])}


def after_insert(mapper, connection, target):
    """
    Listen to a change to the database, if there is one, emit a message to the
    /status end point

    :param mapper: Mapper which is the target of this event.
    :param connection: the Connection being used to emit UPDATE statements for
    this instance. provides a handle into the current transaction on the
    target database specific to this instance.
    :param target: the mapped instance being persisted. If the event is
    configured with raw=True, this will instead be the InstanceState
    state-management object associated with the instance.
    """
    socketio.emit(
        'database insert',
        target.toJSON(),
        namespace='/status'
    )


def after_update(mapper, connection, target):
    """
    Listen to a change to the database, if there is one, emit a message to the
    /status end point

    :param mapper: Mapper which is the target of this event.
    :param connection: the Connection being used to emit UPDATE statements for
    this instance. provides a handle into the current transaction on the
    target database specific to this instance.
    :param target: the mapped instance being persisted. If the event is
    configured with raw=True, this will instead be the InstanceState
    state-management object associated with the instance.
    """
    socketio.emit(
        'database update',
        target.toJSON(),
        namespace='/status'
    )


@socketio.on('connect', namespace='/status')
def connect_status():
    """
    When someone first connects to the WebSocket namespace /status
    """
    emit(
        'connect',
        'connected'
    )


@socketio.on('disconnect', namespace='/status')
def connect_status():
    """
    When someone first connects to the WebSocket namespace /status
    """
    emit(
        'disconnect',
        'disconnected'
    )
