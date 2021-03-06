"""
Application factory
"""

import logging.config
import os

from flask import Flask, send_from_directory
from flask.ext.restful import Api
from flask.ext.cors import CORS
from .views import GithubListener, CommandView, socketio, \
    after_insert, after_update, RabbitMQ, StatusView, \
    ServerSideStorage
from .models import db, Deployment


def create_app(name='ADSDeploy'):
    """
    Create the application

    :param name: name of the application
    :return: flask.Flask application
    """

    app = Flask(name, static_folder='') # set the root of the project
    app.url_map.strict_slashes = False

    # Load config and logging
    load_config(app)
    logging.config.dictConfig(
        app.config['DEPLOY_LOGGING']
    )

    # CORS
    CORS(
        app,
        resources={
            r'/*': {'origins': app.config['CORS_ORIGINS']},
        },
        allow_headers=app.config['CORS_HEADERS'],
        supports_credentials=True
    )

    # Register extensions
    api = Api(app)
    api.add_resource(GithubListener, '/webhooks', methods=['POST'])
    api.add_resource(CommandView, '/command', methods=['GET'])
    api.add_resource(RabbitMQ, '/rabbitmq', methods=['POST'])
    api.add_resource(StatusView, '/status', methods=['GET'])
    api.add_resource(ServerSideStorage, '/store/<string:key>', methods=['GET', 'POST'])
    @app.route('/static/<path:path>')
    def root(path):
        static_folder = app.config.get('STATIC_FOLDER', 'static')
        if not os.path.isabs(static_folder):
            static_folder = os.path.join(app.root_path, static_folder)
        return send_from_directory(static_folder, path)

    # Register any WebSockets
    socketio.init_app(app)

    # Initialise the database
    db.init_app(app)
    # add events
    db.event.listen(Deployment, 'after_insert', after_insert)
    db.event.listen(Deployment, 'after_update', after_update)

    return app


def load_config(app):
    """
    Loads configuration in the following order:
        1. config.py
        2. local_config.py (ignore failures)
        3. consul (ignore failures)
    :param app: flask.Flask application instance
    :param basedir: base directory to load the config from
    :return: None
    """

    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    app.config.from_pyfile(os.path.join(basedir, 'config.py'))

    try:
        app.config.from_pyfile(os.path.join(basedir, 'local_config.py'))
    except IOError:
        app.logger.info("Could not load local_config.py")

if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, use_reloader=False)
