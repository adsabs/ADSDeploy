from ADSDeploy.pipeline import generic

"""Generic handling of error states

TODO: improve this worker"""
        
class ErrorHandler(generic.RabbitMQWorker):
    def process_payload(self, msg):
        pass
