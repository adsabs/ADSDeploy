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
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

SQLALCHEMY_DATABASE_URI = 'sqlite://'
SQLALCHEMY_TRACK_MODIFICATIONS = False

EXCHANGE = 'test'
ROUTE = 'test'

try:
    from ADSDeploy.config import RABBITMQ_URL
except:
    pass