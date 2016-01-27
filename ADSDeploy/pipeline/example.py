

from .. import app
from ADSDeploy.pipeline import generic


class ExampleWorker(generic.RabbitMQWorker):
    """
    Hello world example
    """
    def __init__(self, params=None):
        super(ExampleWorker, self).__init__(params)
        app.init_app()
        
    def process_payload(self, msg, **kwargs):
        """
        :param msg: payload, example:
            {'foo': '....',
            'bar': ['.....']}
        :type: dict
        
        :return: no return
        """
        
        if not isinstance(msg, dict):
            raise Exception('Received unknown payload {0}'.format(msg))
        
        if not msg.get('foo'):
            raise Exception('Unusable payload, missing foo {0}'.format(msg))
        
        # do something with the payload
        result = dict(msg)        
        
        # publish the results into the queue
        self.publish(msg)
