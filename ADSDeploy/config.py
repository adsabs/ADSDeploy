import os
LOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)
LOG_PATH = '{home}/logs'.format(home=LOG_PATH)

if not os.path.isdir(LOG_PATH):
    os.mkdir(LOG_PATH)

# Connection to the database where we save orcid-claims (this database
# serves as a running log of claims and storage of author-related
# information). It is not consumed by others (ie. we 'push' results) 
# SQLALCHEMY_URL = 'postgres://docker:docker@localhost:6432/docker'
SQLALCHEMY_URL = 'sqlite:///'
SQLALCHEMY_ECHO = False


# Configuration of the pipeline; if you start 'vagrant up rabbitmq' 
# container, the port is localhost:6672 - but for production, you 
# want to point to the ADSImport pipeline 
RABBITMQ_URL = 'amqp://guest:guest@127.0.0.1:6672/adsdeploy?' \
               'socket_timeout=10&backpressure_detection=t'
               

# possible values: WARN, INFO, DEBUG
LOGGING_LEVEL = 'DEBUG'
POLL_INTERVAL = 15  # per-worker poll interval (to check health) in seconds.

# All work we do is concentrated into one exchange (the queues are marked
# by topics, e.g. ads.worker.claims); The queues will be created automatically
# based on the workers' definition. If 'durable' = True, it means that the 
# queue is created as permanent *AND* the worker will publish 'permanent'
# messages. Ie. if rabbitmq goes down/restarted, the uncomsumed messages will
# still be there. For an example of a config, see: 
# https://github.com/adsabs/ADSOrcid/blob/master/ADSOrcid/config.py#L53
EXCHANGE = 'ADSDeploy'

WORKERS = {
    'deploy.BeforeDeploy': {
        'concurrency': 1,
        'subscribe': 'ads.deploy.before_deploy',
        'publish': 'ads.deploy.deploy',
        'status': 'ads.deploy.status',
        'error': 'ads.deploy.error',
        'durable': True
    },
    'deploy.Deploy': {
        'concurrency': 1,
        'subscribe': 'ads.deploy.deploy',
        'publish': 'ads.deploy.test',
        'status': 'ads.deploy.status',
        'error': 'ads.deploy.error',
        'durable': True
    },
    'integration_tester.IntegrationTestWorker': {
        'concurrency': 1,
        'subscribe': 'ads.deploy.test',
        'publish': 'ads.deploy.after_deploy',
        'status': 'ads.deploy.status',
        'error': 'ads.deploy.error',
        'durable': True
    },
    'deploy.AfterDeploy': {
        'concurrency': 1,
        'subscribe': 'ads.deploy.after_deploy',
        'publish': None,
        'error': 'ads.deploy.error',
        'durable': True
    },
    'errors.ErrorHandler': {
        'subscribe': 'ads.deploy.error',
        'status': 'ads.deploy.status',
        'publish': None,
        'durable': False
    },
    'deploy.Restart': {
        'concurrency': 1,
        'subscribe': 'ads.deploy.restart',
        'publish': 'ads.deploy.after_deploy',
        'error': 'ads.deploy.error',
        'durable': True
    },
    'db_writer.DatabaseWriterWorker': {
        'concurrency': 1,
        'subscribe': 'ads.deploy.status',
        'publish': None,
        'error': 'ads.deploy.error',
        'durable': True
    }
}

# the eb-deploy by default lives on the same level as ADSDeploy
EB_DEPLOY_HOME = os.path.abspath(os.path.join(os.path.abspath(__file__), '../eb-deploy')) 

# Web Application configuration parameters
WEBAPP_URL = '127.0.0.1:9000'

# Include here any other configuration options. These will be made available
# to workers via app.config


# Web Application
GITHUB_SIGNATURE_HEADER = 'X-Hub-Signature'
GITHUB_SECRET = 'redacted'
GITHUB_COMMIT_API = 'https://api.github.com/repos/adsabs/{repo}/git/commits/{hash}'
GITHUB_TAG_FIND_API = 'https://api.github.com/repos/adsabs/{repo}/git/refs/tags/{tag}'
GITHUB_TAG_GET_API = 'https://api.github.com/repos/adsabs/{repo}/git/tags/{hash}'
AWS_REGION = 'us-east-1'
AWS_ACCESS_KEY = 'redacted'
AWS_SECRET_KEY = 'redacted'

DEPLOY_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(levelname)s\t%(process)d '
                      '[%(asctime)s]:\t%(message)s',
            'datefmt': '%m/%d/%Y %H:%M:%S',
        }
    },
    'handlers': {
        'console': {
            'formatter': 'default',
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
        'file': {
            'filename': '{}/webapp.log'.format(LOG_PATH),
            'formatter': 'default',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': 'DEBUG'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

SQLALCHEMY_DATABASE_URI = SQLALCHEMY_URL
SQLALCHEMY_TRACK_MODIFICATIONS = SQLALCHEMY_ECHO

WEBAPP_EXCHANGE = 'test'
WEBAPP_ROUTE = 'test'

CORS_ORIGINS = '*'
CORS_HEADERS = ['Content-Type', 'X-BB-Api-Client-Version', 'Authorization', 'Accept']

