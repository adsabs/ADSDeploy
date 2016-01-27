"""
Custom exceptions
"""

class NoSignatureInfo(Exception):
    """
    Raised when no signature info is found
    """


class InvalidSignature(Exception):
    """
    Raised when the signature is not validated
    """


class UnknownRepoError(Exception):
    """
    Raised when a repo is not known to mc
    """


class UnknownServiceError(Exception):
    """
    Raised when a service is not known to mc
    """


class TimeOutError(Exception):
    """
    Raised when a generic function does not respond after a given time
    """