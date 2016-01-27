#!/usr/bin/env python
"""

Main script for controlling the ADSDeploy
"""

__author__ = ''
__maintainer__ = ''
__copyright__ = 'Copyright 2016'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

import sys
import time
import pika
import argparse
import json
from ADSDeploy import app
from ADSDeploy.pipeline.example import ExampleWorker
from ADSDeploy.pipeline import generic
from ADSDeploy.pipeline import pstart
from ADSDeploy.utils import setup_logging

logger = setup_logging(__file__, __name__)


def purge_queues(queues):
    """
    Purges the queues on the RabbitMQ instance of its content

    :param queues: queue name that needs to be purged
    :return: no return
    """

    publish_worker = generic.RabbitMQWorker()
    publish_worker.connect(app.config.get('RABBITMQ_URL'))

    for worker, wconfig in app.config.get('WORKERS').iteritems():
            for x in ('publish', 'subscribe'):
                if x in wconfig and wconfig[x]:
                    try:
                        publish_worker.channel.queue_delete(queue=wconfig[x])
                    except pika.exceptions.ChannelClosed, e:
                        pass


def run_example(claims_file, queue='example', **kwargs):
    """
    Reads input from a file and sends it to the queue
    
    :param: claims_file - path to the claims
    :type: str
    :param: queue - where to send the claims
    :type: str (example)
    
    :return: no return
    """

    logger.info('Loading records from: {0}'.format(claims_file))
    worker = ExampleWorker(params={
                        'publish': queue,
                        'exchange': app.config.get('EXCHANGE', 'ADSDeploy-exchange')
                    })
    i = 0
    worker.connect(app.config.get('RABBITMQ_URL'))
    with open(claims_file, 'r') as f:
        for line in f:
            worker.publish(line)
            i+=1
        
    logger.info('Done processing {0} claims.'.format(i))


def start_pipeline():
    """Starts the workers and let them do their job"""
    pstart.start_pipeline({}, app)
    

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Process user input.')


    parser.add_argument('-q',
                        '--purge_queues',
                        dest='purge_queues',
                        action='store_true',
                        help='Purge all the queues so there are no remaining'
                             ' packets')

    parser.add_argument('-e',
                        '--run_example',
                        dest='run_example',
                        action='store',
                        type=str,
                        help='Path to input file to import')
    
    parser.add_argument('-p',
                        '--start_pipeline',
                        dest='start_pipeline',
                        action='store_true',
                        help='Start the pipeline')
    
    parser.set_defaults(purge_queues=False)
    parser.set_defaults(start_pipeline=False)
    args = parser.parse_args()
    
    app.init_app()
    
    work_done = False
    if args.purge_queues:
        purge_queues(app.config.get('WORKERS'))
        sys.exit(0)

    if args.start_pipeline:
        start_pipeline()
        work_done = True
        
    if args.import_claims:
        # Send the files to be put on the queue
        run_example(args.import_claims)
        work_done = True
        
    if not work_done:
        parser.print_help()
        sys.exit(0)