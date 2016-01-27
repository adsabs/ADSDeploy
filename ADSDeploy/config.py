# Connection to the database where we save orcid-claims (this database
# serves as a running log of claims and storage of author-related
# information). It is not consumed by others (ie. we 'push' results) 
# SQLALCHEMY_URL = 'postgres://docker:docker@localhost:6432/docker'
SQLALCHEMY_URL = 'sqlite:///'
SQLALCHEMY_ECHO = False


# Configuration of the pipeline; if you start 'vagrant up rabbitmq' 
# container, the port is localhost:8072 - but for production, you 
# want to point to the ADSImport pipeline 
RABBITMQ_URL = 'amqp://guest:guest@172.17.0.1:6672/?' \
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
    'errors.ErrorHandler': {
        'subscribe': None,
        'exchange': None,
        'publish': None,
        'durable': False
    }
}


# Web Application configuration parameters
WEBAPP_URL = '172.17.0.1:9000'

GITHUB_SIGNATURE_HEADER = 'X-Hub-Signature'
GITHUB_SECRET = 'redacted'
GITHUB_COMMIT_API = 'https://api.github.com/repos/adsabs/{repo}/git/commits/{hash}'
GITHUB_TAG_FIND_API = 'https://api.github.com/repos/adsabs/{repo}/git/refs/tags/{tag}'
GITHUB_TAG_GET_API = 'https://api.github.com/repos/adsabs/{repo}/git/tags/{hash}'
AWS_REGION = 'us-east-1'
AWS_ACCESS_KEY = 'redacted'
AWS_SECRET_KEY = 'redacted'

WATCHED_REPOS = [
    'adsws',
    'solr-service',
    'export_service',
    'graphics_service',
    'recommender_service',
    'citation_helper_service',
    'metrics_service',
    'vis-services',
    'biblib-service',
    'orcid-service',
    'myads',
    'object_service',
    'harbour-service'
]

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
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Include here any other configuration options. These will be made available 
# to workers via app.config